#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo_root"

if [[ -z "${VIRTUAL_ENV:-}" && -x "$repo_root/.venv/bin/python" ]]; then
    PATH="$repo_root/.venv/bin:$PATH"
    export PATH
fi

python -m ruff check .
python -m black --check --workers 1 .
python -m mypy src
python -m pytest
