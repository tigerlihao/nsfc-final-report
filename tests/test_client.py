import base64
import json
import os
from Crypto.Cipher import DES

import nsfc_final_report.client as client_mod


def pad_pkcs7(b: bytes, block_size: int = 8) -> bytes:
    pad_len = block_size - (len(b) % block_size)
    return b + bytes([pad_len]) * pad_len


def encrypt_des_ecb(plaintext: bytes, key: bytes) -> str:
    cipher = DES.new(key, DES.MODE_ECB)
    ct = cipher.encrypt(pad_pkcs7(plaintext, 8))
    return base64.b64encode(ct).decode("ascii")


def test_des_decrypt_roundtrip():
    c = client_mod.NSFCClient()
    sample = b'{"hello": "world"}'
    b64 = encrypt_des_ecb(sample, client_mod.DES_KEY)
    dec = c._des_decrypt(b64)
    assert dec == sample


class DummyResp:
    def __init__(
        self, text="", json_obj=None, status_code=200, content=b"", headers=None
    ):
        self.text = text
        self._json = json_obj
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            # emulate requests.HTTPError having response attribute
            err = Exception("HTTP error")
            err.response = self
            raise err


def test_search_plaintext_fallback(monkeypatch):
    c = client_mod.NSFCClient()

    def fake_post(url, json=None, headers=None, timeout=None):
        return DummyResp(text="not-a-base64", json_obj={"data": {"resultsData": []}})

    monkeypatch.setattr(c.session, "post", fake_post)
    res = c.search(fuzzyKeyword="x")
    assert isinstance(res, dict)
    assert res.get("data") is not None


def test_search_decrypted_json(monkeypatch):
    c = client_mod.NSFCClient()
    payload = {"ok": True}
    b64 = encrypt_des_ecb(json.dumps(payload).encode("utf-8"), client_mod.DES_KEY)

    def fake_post(url, json=None, headers=None, timeout=None):
        return DummyResp(text=b64, json_obj=None)

    monkeypatch.setattr(c.session, "post", fake_post)
    res = c.search(fuzzyKeyword="x")
    assert res == payload


def test_download_report_writes_files_and_respects_force(monkeypatch, tmp_path):
    c = client_mod.NSFCClient()

    # monkeypatch get_report_page_url to return one page, then None
    def fake_get_report_page_url(self, pid, idx):
        if idx == 1:
            return "http://example.com/page1"
        return None

    monkeypatch.setattr(
        client_mod.NSFCClient, "get_report_page_url", fake_get_report_page_url
    )

    # simulate session.get behavior: return a successful DummyResp
    def fake_get(url, timeout=None, headers=None):
        return DummyResp(
            status_code=200, content=b"PNGDATA", headers={"Content-Type": "image/png"}
        )

    monkeypatch.setattr(c.session, "get", fake_get)

    out_dir = tmp_path / "out"
    out_dir = str(out_dir)
    files = c.download_report("P123", out_dir=out_dir, max_pages=5, force=False)
    # should have written one file page_001.png
    expected = os.path.join(out_dir, "page_001.png")
    assert expected in files
    assert os.path.exists(expected)

    # call again without force: file exists and should be included but not re-downloaded (still present)
    files2 = c.download_report("P123", out_dir=out_dir, max_pages=5, force=False)
    assert expected in files2

    # call with force: should attempt to overwrite (we simulate success)
    files3 = c.download_report("P123", out_dir=out_dir, max_pages=5, force=True)
    assert expected in files3


def test_download_report_retry_on_transient_error(monkeypatch, tmp_path):
    c = client_mod.NSFCClient()

    def fake_get_report_page_url(self, pid, idx):
        if idx == 1:
            return "http://example.com/page1"
        return None

    monkeypatch.setattr(
        client_mod.NSFCClient, "get_report_page_url", fake_get_report_page_url
    )

    calls = {"n": 0}

    def fake_get(url, timeout=None, headers=None):
        calls["n"] += 1
        if calls["n"] == 1:
            # first call raises, causing a retry
            raise Exception("transient")
        return DummyResp(
            status_code=200, content=b"JPGDATA", headers={"Content-Type": "image/jpeg"}
        )

    monkeypatch.setattr(c.session, "get", fake_get)

    out_dir = str(tmp_path / "out2")
    files = c.download_report("P456", out_dir=out_dir, max_pages=3, force=True)
    assert len(files) == 1
    assert calls["n"] >= 2
