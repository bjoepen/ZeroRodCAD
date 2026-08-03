#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m compileall tools src tests packaging/macos
python -m ruff check .
python -m ruff format --check .
pre-commit run --all-files
python tools/scan_bundle.py --version
python -m tools.scan_bundle --version
python tools/benchmark_analysis.py --version
python tools/trace_runtime.py --version

# Non-mutating smoke coverage: deterministic JSON, dynamic imports, controlled
# launch failure, timeout, cleanup and the temporary minimal-app fixture.
python -m pytest -q \
  tests/test_runtime_trace_models.py \
  tests/test_runtime_trace_imports.py \
  tests/test_runtime_trace_tool.py

echo "Build 021 Milestone M1 validation passed."
