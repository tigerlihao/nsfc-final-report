#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage: ./scripts/uv_tasks.sh <task>
Tasks:
  venv     - create venv with `uv venv .venv`
  install  - install test/dev deps (uv add preferred)
  lint     - run linters (ruff, black, isort)
  test     - run pytest with coverage
  ci       - run venv -> install -> lint -> test
  format   - format code (ruff/isort/black)
  publish  - build (and optionally upload with UPLOAD=true)
EOF
}

task=${1:-}
if [ -z "$task" ]; then usage; exit 2; fi

case "$task" in
  venv)
    python -m pip install --upgrade pip
    pip install uv
    uv venv .venv
    ;;
  install)
    . .venv/bin/activate
    if command -v uv >/dev/null 2>&1; then
      uv pip install -e ".[dev]" || python -m pip install -r requirements.txt
    else
      python -m pip install -r requirements.txt || python -m pip install pytest pytest-cov ruff black isort
    fi
    ;;
  lint)
    . .venv/bin/activate
    ruff check . && black --check . && isort --check-only .
    ;;
  test)
    . .venv/bin/activate
    pytest -q --cov=nsfc_final_report --cov-report=term-missing
    ;;
  ci)
    ./scripts/uv_tasks.sh venv
    ./scripts/uv_tasks.sh install
    ./scripts/uv_tasks.sh lint
    ./scripts/uv_tasks.sh test
    ;;
  format)
    . .venv/bin/activate
    ruff format . || true
    isort . || true
    black . || true
    ;;
  publish)
    python -m pip install --upgrade pip
    python -m pip install build twine
    python -m build
    if [ "${UPLOAD:-}" = "true" ]; then
      twine upload dist/*
    else
      echo "Build complete. To upload set UPLOAD=true and provide TWINE_USERNAME/TWINE_PASSWORD (or use CI secrets)"
    fi
    ;;
  *)
    echo "Unknown task: $task" >&2
    usage
    exit 2
    ;;
esac
