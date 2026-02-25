---
name: nsfc-final-report
description: Search NSFC final project conclusions, fetch project info, and download multi-page conclusion report images. Use when needing to programmatically query or retrieve NSFC final report content via the kd.nsfc.cn APIs.
---

This skill bundles a Python package (nsfc_final_report) that provides:

- search(fuzzyKeyword,pageNum,pageSize,...) -> dict  — calls /completionQueryResultsData and DES-decrypts results with key IFROMC86.
- get_project_info(project_id) -> dict — calls /conclusionProjectInfo/{id} and returns JSON.
- download_report(project_id, out_dir=None) -> List[str] — page-by-page calls to /completeProjectReport, downloads images until 404 and saves them to out_dir (defaults to data/reports/<project_id> in the current working directory).

Implementation notes:
- Uses requests and pycryptodome (DES ECB with PKCS#5/7 padding assumed).
- Default base URL: https://kd.nsfc.cn
- Authorization header uses `Bearer false` to emulate browser requests.

Files:
- nsfc_final_report/  — python package
- pyproject.toml      — project metadata
- skill/SKILL.md      — this file

When using the skill in OpenClaw, call the Python API or the CLI entrypoint `nsfc-final-report`.
