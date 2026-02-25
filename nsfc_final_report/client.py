import base64
import logging
import os
import time
from typing import Dict, List, Optional

import requests
from Crypto.Cipher import DES

DEFAULT_BASE = "https://kd.nsfc.cn"

_env_key = os.environ.get("NSFC_DES_KEY")
if _env_key:
    if isinstance(_env_key, str):
        _key_bytes = _env_key.encode("utf-8")
    else:
        _key_bytes = _env_key
    if len(_key_bytes) != 8:
        raise ValueError("NSFC_DES_KEY must be exactly 8 bytes long")
    DES_KEY = _key_bytes
else:
    DES_KEY = b"IFROMC86"  # historical default (8 bytes)
    logging.getLogger(__name__).warning(
        "Using hard-coded DES key; set NSFC_DES_KEY env var to override"
    )


class NSFCClient:
    def __init__(self, base_url: str = DEFAULT_BASE, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://kd.nsfc.cn",
            "Referer": "https://kd.nsfc.cn",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Authorization": "Bearer false",
        }

    def _des_decrypt(self, b64_ciphertext: str) -> bytes:
        """Decrypt base64 DES ECB (no padding or PKCS5/7?)
        The API returns a DES ECB encrypted JSON; we assume PKCS5/7 padding.
        """
        data = base64.b64decode(b64_ciphertext)
        cipher = DES.new(DES_KEY, DES.MODE_ECB)
        plain = cipher.decrypt(data)
        # remove PKCS#5/7 padding
        pad = plain[-1]
        if isinstance(pad, str):
            pad = ord(pad)
        return plain[:-pad]

    def search(
        self, fuzzyKeyword: str = "", pageNum: int = 0, pageSize: int = 10, **kwargs
    ) -> Dict:
        url = f"{self.base_url}/api/baseQuery/completionQueryResultsData"
        payload = {
            "complete": True,
            "fuzzyKeyword": fuzzyKeyword,
            "isFuzzySearch": True,
            "conclusionYear": kwargs.get("conclusionYear", ""),
            "dependUnit": kwargs.get("dependUnit", ""),
            "keywords": kwargs.get("keywords", ""),
            "pageNum": pageNum,
            "pageSize": pageSize,
            "projectType": kwargs.get("projectType", ""),
            "projectTypeName": kwargs.get("projectTypeName", ""),
            "code": kwargs.get("code", ""),
            "ratifyYear": kwargs.get("ratifyYear", ""),
            "order": kwargs.get("order", "enddate"),
            "ordering": kwargs.get("ordering", "desc"),
            "codeScreening": "",
            "dependUnitScreening": "",
            "keywordsScreening": "",
            "projectTypeNameScreening": "",
        }
        r = self.session.post(
            url, json=payload, headers=self.headers, timeout=self.timeout
        )
        r.raise_for_status()
        enc = r.text
        # response is DES ECB encrypted JSON, base64 encoded
        try:
            dec = self._des_decrypt(enc)
        except Exception:
            # some endpoints may return plaintext JSON
            return r.json()
        import json as _json

        return _json.loads(dec.decode("utf-8"))

    def search_all(self, fuzzyKeyword: str = "", pageSize: int = 10, **kwargs):
        """Iterate through all pages of search results and yield raw result entries.
        Each page's JSON has data.resultsData which is a list of result rows.

        pageNum starts at 0 and increments by 1 each loop.
        """
        page = 0
        import time

        while True:
            # retry search on transient errors
            for attempt in range(1, 4):
                try:
                    res = self.search(
                        fuzzyKeyword=fuzzyKeyword,
                        pageNum=page,
                        pageSize=pageSize,
                        **kwargs,
                    )
                    break
                except Exception:
                    if attempt < 3:
                        time.sleep(2 ** (attempt - 1))
                        continue
                    else:
                        raise
            data = res.get("data", {})
            results = data.get("resultsData", [])
            if not results:
                break
            for row in results:
                yield row
            itotal = data.get("itotalRecords")
            # stop if we've covered all
            if itotal is not None:
                already = (page + 1) * pageSize
                if already >= int(itotal):
                    break
            page += 1

    def batch_fetch(
        self,
        fuzzyKeyword: str = "",
        out_dir: Optional[str] = None,
        pageSize: int = 50,
        force: bool = False,
        jsonl_path: Optional[str] = None,
        **kwargs,
    ) -> List[str]:
        """Perform full search (all pages), write each search-result row to a jsonl file, then for each project id fetch detailed info and download report.

        - jsonl_path: path to write search results (defaults to <out_dir>/search_results.jsonl)
        - For each project, create dir <out_dir>/<project_id>/ and save info.json and report pages there.
        Returns list of project ids processed.
        """
        import json

        if out_dir is None:
            out_dir = os.path.join(os.getcwd(), "data", "batch")
        os.makedirs(out_dir, exist_ok=True)
        if jsonl_path is None:
            jsonl_path = os.path.join(out_dir, "search_results.jsonl")
        processed = []
        # write search results
        with open(jsonl_path, "w", encoding="utf-8") as jf:
            for row in self.search_all(
                fuzzyKeyword=fuzzyKeyword, pageSize=pageSize, **kwargs
            ):
                # row is a list per observed format; try to extract id and basic fields
                try:
                    proj_id = row[0]
                except Exception:
                    proj_id = None
                obj = {"project_id": proj_id, "raw": row}
                jf.write(json.dumps(obj, ensure_ascii=False) + "\n")
        # now iterate jsonl and fetch details + reports
        with open(jsonl_path, "r", encoding="utf-8") as jf:
            for line in jf:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                pid = obj.get("project_id")
                if not pid:
                    continue
                pdir = os.path.join(out_dir, pid)
                os.makedirs(pdir, exist_ok=True)
                # fetch project info with retries; always write an info.json (success or error)
                info = None
                info_path = os.path.join(pdir, "info.json")
                for attempt in range(1, 4):
                    try:
                        info = self.get_project_info(pid)
                        break
                    except Exception as e:
                        last_exc = e
                        time.sleep(1 if attempt == 1 else 2)
                        continue
                if info is not None:
                    try:
                        with open(info_path, "w", encoding="utf-8") as fih:
                            json.dump(info, fih, ensure_ascii=False, indent=2)
                    except Exception:
                        # best-effort write
                        pass
                else:
                    # write an error placeholder so directory is not empty
                    try:
                        with open(info_path, "w", encoding="utf-8") as fih:
                            json.dump(
                                {"error": f"failed to fetch info: {repr(last_exc)}"},
                                fih,
                                ensure_ascii=False,
                                indent=2,
                            )
                    except Exception:
                        pass

                # download report into project dir; capture errors into errors.json if any
                try:
                    files = self.download_report(
                        pid, out_dir=pdir, max_pages=50, force=force
                    )
                    # write a manifest of downloaded files
                    try:
                        with open(
                            os.path.join(pdir, "files.json"), "w", encoding="utf-8"
                        ) as ff:
                            json.dump(files, ff, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        with open(
                            os.path.join(pdir, "errors.json"), "w", encoding="utf-8"
                        ) as ef:
                            json.dump(
                                {"download_error": repr(e)},
                                ef,
                                ensure_ascii=False,
                                indent=2,
                            )
                    except Exception:
                        pass
                processed.append(pid)
        return processed

    def get_project_info(self, project_id: str) -> Dict:
        url = f"{self.base_url}/api/baseQuery/conclusionProjectInfo/{project_id}"
        r = self.session.post(
            url,
            headers={
                **self.headers,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def get_report_page_url(self, project_id: str, index: int) -> Optional[str]:
        url = f"{self.base_url}/api/baseQuery/completeProjectReport"
        payload = {"id": project_id, "index": index}
        r = self.session.post(
            url,
            data=payload,
            headers={
                **self.headers,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        j = r.json()
        if not j or j.get("code") != 200:
            return None
        url_path = j.get("data", {}).get("url")
        if not url_path:
            return None
        return f"{self.base_url}{url_path}"

    def download_report(
        self,
        project_id: str,
        out_dir: Optional[str] = None,
        max_pages: int = 50,
        force: bool = False,
    ) -> List[str]:
        if out_dir is None:
            out_dir = os.path.join(os.getcwd(), "data", "reports", project_id)
        os.makedirs(out_dir, exist_ok=True)
        downloaded = []
        import time

        for idx in range(1, max_pages + 1):
            img_url = self.get_report_page_url(project_id, idx)
            if not img_url:
                break
            success = False
            for attempt in range(1, 4):
                try:
                    # include Referer header to mimic browser fetching the image
                    resp = self.session.get(
                        img_url,
                        timeout=self.timeout,
                        headers={
                            **self.headers,
                            "Referer": f"https://kd.nsfc.cn/finalDetails?id={project_id}",
                        },
                    )
                    if resp.status_code == 404:
                        success = False
                        break
                    resp.raise_for_status()
                    ext = "jpg"
                    content_type = resp.headers.get("Content-Type", "")
                    if "png" in content_type:
                        ext = "png"
                    filename = os.path.join(out_dir, f"page_{idx:03d}.{ext}")
                    if not force and os.path.exists(filename):
                        # skip existing file
                        downloaded.append(filename)
                        success = True
                        break
                    with open(filename, "wb") as fh:
                        fh.write(resp.content)
                    downloaded.append(filename)
                    success = True
                    break
                except requests.HTTPError as e:
                    code = getattr(e.response, "status_code", None)
                    if code == 404:
                        success = False
                        break
                    # on 503/429/403 try backoff and retry a few times, otherwise give up on this page
                    if attempt < 3:
                        backoff = 2 ** (attempt - 1)
                        time.sleep(backoff)
                        continue
                    else:
                        # give up this page and continue to next
                        break
                except Exception:
                    if attempt < 3:
                        time.sleep(2 ** (attempt - 1))
                        continue
                    else:
                        break
            if not success:
                # stop if the page was 404 (no more pages) or if we couldn't retrieve after retries
                # If it's a transient failure we continue to next page; conservative approach: stop on first non-success
                break
        return downloaded
