nsfc-final-report

Python library and OpenClaw skill to search and download NSFC final project conclusion reports.

Features:
- Search NSFC final project conclusions (DES-ECB encrypted responses are decrypted using key IFROMC86).
- Fetch project basic information by project id.
- Download multi-page conclusion report images (auto-stop on 404). Default saves to data/reports/<project_id>.

Usage (CLI):
- Activate project virtualenv: source .venv/bin/activate
- Search: nsfc-final-report search --keyword 心肌 --page 0 --size 10
- Get info: nsfc-final-report info <project_id>
- Download (default max-pages=50, skip existing files): nsfc-final-report download <project_id> --out /path/to/dir
- Download forcing re-download: nsfc-final-report download <project_id> --force

Behavior notes:
- Default max pages is 50. Change with --max-pages.
- By default existing files in target folder are not re-downloaded (unless --force is provided).
 - DES key: the code now prefers an environment variable `NSFC_DES_KEY` (exactly 8 bytes) for the DES ECB key.
   If `NSFC_DES_KEY` is not set the historical default `IFROMC86` is used for backward compatibility,
   but a warning is emitted. To set the env var locally:
   - Bash / macOS / Linux: `export NSFC_DES_KEY=IFROMC86` (replace with your 8-byte secret)
   - Windows PowerShell: `$env:NSFC_DES_KEY = 'IFROMC86'`
   Note: the key must be exactly 8 bytes long; otherwise the client raises a ValueError. In CI, store the
   secret in repository secrets and inject it into the job environment rather than committing it to source.

Development:
- Create venv with uv: uv venv .venv
- Install deps with uv: uv add requests pycryptodome

Security:
- Do not commit sensitive keys if you prefer to move IFROMC86 to an environment variable.
