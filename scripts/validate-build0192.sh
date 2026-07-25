#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m compileall tools tests
python -m ruff check .
python -m ruff format --check .
pre-commit run --all-files
python tools/scan_bundle.py --version
python -m tools.scan_bundle --version

echo "Build 019.2 validation passed."
