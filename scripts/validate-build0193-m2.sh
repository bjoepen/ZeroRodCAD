#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m compileall tools src tests
python -m ruff check .
python -m ruff format --check .

if command -v pre-commit >/dev/null 2>&1; then
  pre-commit run --all-files
else
  echo "Hinweis: pre-commit ist nicht installiert; die übrigen Release-Gates wurden ausgeführt."
fi

echo "Build 019.3 Milestone M2 validation passed."
