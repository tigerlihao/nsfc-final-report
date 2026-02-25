**Agents**
- Purpose: guidance for agentic coding assistants (how to build, run, lint, test, and style) for this repository. See `README.md` for CLI usage and `scripts/` for helpers.

- Quick setup: create a Python venv, install deps, activate it.
  - `uv venv .venv` (project uses `uv` in README) or `python -m venv .venv`
  - `source .venv/bin/activate`
  - Install deps: `uv add requests pycryptodome` or `pip install -r requirements.txt` if a requirements file exists.

- Build / Run commands (project is a Python CLI):
  - Run the CLI tool: `nsfc-final-report <command> [args]` (see `README.md`)
  - Run script directly: `python scripts/ocr_reports.py` or `python scripts/batch_ocr.py` as needed.

- Test commands:
  - Run all tests (pytest): `pytest` (recommended when tests are present)
  - Run a single pytest test: `pytest path/to/test_file.py::test_name -q` (this runs only the named test)
  - Run a single unittest test: `python -m unittest path.to.test_module.TestClass.test_method`
  - If the repository uses no test framework yet, create tests under `tests/` and run with `pytest`.

- Lint / Format / Type check (recommended toolchain):
  - Format: `black .` (run before committing)
  - Import sort: `isort .` (or `isort --profile black .`)
  - Lint/fast checks: `ruff check .` or `flake8 .` if configured
  - Type check: `mypy .` (keep stub/ignore rules minimal)
  - Fix issues automatically if supported: `ruff format .` then `black .` then `isort .`

- Running pre-commit locally (if configured):
  - `pre-commit run --all-files`

- Git / commit guidance for agents:
  - Do not create commits unless explicitly requested by the human.
  - If asked to commit, follow the project's commit style: short imperative subject (1 line), optional body explaining why.
  - Never amend or force-push already-pushed commits without explicit permission.

- Coding style and conventions
  - Formatting: use `black` defaults; 88-char line length unless the project explicitly uses another limit.
  - Imports: group and order imports as: stdlib, third-party, local (use `isort` to enforce); avoid wildcard imports.
  - Module names and files: lowercase with underscores (snake_case), short and descriptive. Keep top-level package layout minimal.
  - Functions & variables: `snake_case`.
  - Classes: `PascalCase` (CapWords / CamelCase for class names).
  - Constants: `UPPER_SNAKE_CASE`.
  - Private names: single leading underscore for internal helpers (`_helper`).

- Types and typing
  - Prefer explicit type hints on public functions and module-level APIs; use `-> None` for functions that return nothing.
  - Use `typing` primitives (`list[str]`, `dict[str, Any]`) with Python 3.9+ native generics where convenient.
  - Keep runtime checks minimal — prefer static checking with `mypy` for surprises.
  - Use `Optional[T]` instead of `Union[T, None]` for readability.

- Naming conventions (practical rules)
  - Function names: verbs, short: `download_report`, `fetch_info`.
  - CLI entrypoint: keep small wrapper that parses args and calls well-tested functions.
  - Boolean variables: `is_`, `has_`, `should_` prefixes for clarity.

- Error handling
  - Do not catch broad `Exception` unless re-raising or adding context. Prefer specific exceptions.
  - Raise custom exceptions for library-level errors when callers may want to handle them.
  - Surface errors at CLI boundary: catch exceptions in `if __name__ == '__main__'` wrapper or CLI entrypoint, log user-friendly messages and exit with nonzero code.
  - Use `logging.exception()` when logging an exception's traceback; avoid `print` in libraries.

- Logging
  - Use the standard `logging` module; configure formatting and level only in the top-level entrypoint.
  - Libraries should get a module logger: `logger = logging.getLogger(__name__)` and not call `basicConfig()`.

- Docstrings and inline docs
  - Use short one-line docstring summary followed by an empty line and longer description if needed (Google-style or reStructuredText is acceptable).
  - Document parameters and return values for public functions.

- Tests and test design
  - Keep unit tests in `tests/` and name test files `test_*.py`.
  - Write focused unit tests for pure functions; use small integration tests for HTTP/IO behavior and mark them so they can be skipped or run separately.
  - Use fixtures for shared setup and `monkeypatch` for patching network/IO.

- Secrets and configuration
  - Do not hard-code secrets; move keys (for example the DES key referenced in `README.md` as `IFROMC86`) to environment variables or a vault.
  - Use `os.environ.get('MY_SECRET')` and fail fast with a clear error if required secrets are missing in runtime environments.

- Files and places to check
  - `README.md` — project overview and CLI examples
  - `scripts/` — helper scripts used by the project (`scripts/ocr_reports.py`, `scripts/batch_ocr.py`)

- Cursor/Copilot rules
  - Cursor rules: none found in `.cursor/rules/` or `.cursorrules`.
  - GitHub Copilot rules: none found in `.github/copilot-instructions.md`.

- Agent behavior and safety
  - Read `README.md` and project code before making changes.
  - If blocked by ambiguity that affects correctness, ask one targeted question and include a recommended default.
  - When making edits: prefer small, well-tested changes and include a concise commit message if asked to commit.
  - Avoid destructive git operations; do not `reset --hard` or force-push without explicit permission.

- Useful commands summary (copy-paste):
  - Setup venv with uv: `uv venv .venv`
  - Activate: `source .venv/bin/activate`
  - Install deps with uv: `uv add requests pycryptodome` (or `pip install -r requirements.txt`)
  - Run CLI: `nsfc-final-report search --keyword 心肌 --page 0 --size 10`
  - Run single pytest test: `pytest tests/test_module.py::test_name -q`
  - Format: `black . && isort .`

If you want me to enforce these rules by adding linters, tests, or pre-commit config, tell me which tools to add (e.g. `black`, `isort`, `ruff`, `mypy`, `pytest`) and I'll create the configs and CI changes.
