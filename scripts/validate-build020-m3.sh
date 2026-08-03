#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m compileall tools src tests
python -m ruff check .
python -m ruff format --check .
pre-commit run --all-files
python tools/scan_bundle.py --version
python -m tools.scan_bundle --version
python scripts/smoke-report-engine.py

printf '%s\n' "Build 020 Milestone M3 validation passed."
