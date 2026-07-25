#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m compileall tools src tests
python -m ruff check .
python -m ruff format --check .
pre-commit run --all-files

printf '\nBuild 019.3 Milestone M3 validation passed.\n'
