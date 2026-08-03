#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m compileall tools src tests
python -m ruff check .
python -m ruff format --check .
pre-commit run --all-files
python tools/scan_bundle.py --version
python -m tools.scan_bundle --version
python tools/benchmark_analysis.py --version
python scripts/smoke-benchmark-analysis.py

if grep -RniE '019\.3-M4|020-M1|020-M2|020-M3|BUILD_VERSION' tools src; then
  printf '%s\n' "Legacy productive build metadata found." >&2
  exit 1
fi

printf '%s\n' "Build 020 Milestone M4 validation passed."
