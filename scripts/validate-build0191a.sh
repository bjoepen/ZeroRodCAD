#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  printf 'FEHLER: Keine virtuelle Python-Umgebung aktiv.\n' >&2
  printf 'Aktivieren: source .venv/bin/activate\n' >&2
  exit 2
fi

python -m pytest tests/test_scanner2.py tests/test_scanner2_classification.py
python -m compileall tools tests
python -m ruff check tools tests
python -m ruff format --check tools tests
pre-commit run --all-files
