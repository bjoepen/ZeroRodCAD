#!/usr/bin/env bash
set -euo pipefail

python -m pytest tests/test_deadlibs_foundation.py
python -m compileall tools/bundle_analyzer/deadlibs tests/test_deadlibs_foundation.py
python -m ruff check tools/bundle_analyzer/deadlibs tests/test_deadlibs_foundation.py
python -m ruff format --check tools/bundle_analyzer/deadlibs tests/test_deadlibs_foundation.py

echo "Build 019.3 Milestone M1 validation passed."
