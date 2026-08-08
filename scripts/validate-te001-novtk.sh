#!/usr/bin/env bash
# TE-001 No-VTK feasibility validation. Never touches the productive .venv.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/te001-novtk-poc"
POC_VENV=".venv-novtk-poc"
POC_PYTHON="${POC_VENV}/bin/python"

echo "== TE-001: verifying Python 3.13 =="
if ! command -v python3.13 >/dev/null 2>&1; then
  echo "python3.13 not found on PATH" >&2
  exit 1
fi
python3.13 -c "import sys; assert sys.version_info[:2] == (3, 13), sys.version" \
  || { echo "python3.13 did not report version 3.13.x" >&2; exit 1; }

echo "== TE-001: preparing isolated venv (${POC_VENV}) =="
if [ ! -x "${POC_PYTHON}" ]; then
  python3.13 -m venv "${POC_VENV}"
fi

echo "== TE-001: verifying venv isolation (no system-site-packages) =="
"${POC_PYTHON}" - <<'PY'
import sys
assert sys.prefix != sys.base_prefix, "venv is not isolated from the base interpreter"
print("prefix:", sys.prefix)
print("base_prefix:", sys.base_prefix)
print("version:", sys.version)
PY

echo "== TE-001: installing pinned dependencies (skipped if cadquery already present) =="
if ! "${POC_PYTHON}" -c "import cadquery" >/dev/null 2>&1; then
  "${POC_PYTHON}" -m pip install --upgrade pip
  "${POC_PYTHON}" -m pip install "cadquery-ocp-novtk==7.9.3.1.1"
  "${POC_PYTHON}" -m pip install "cadquery==2.8.0" --no-deps
  "${POC_PYTHON}" -m pip install \
    "ezdxf>=1.3.0" "multimethod<2.0,>=1.11" "nlopt<3.0,>=2.9.0" "runtype" "casadi" \
    "pyparsing>=3.0.0" "scipy" "numba"
  "${POC_PYTHON}" -m pip install -e . --no-deps
fi
# Note: `import cadquery` is expected to fail under this venv (see
# docs/research/TE-001-No-VTK/Results.md) — the check above only skips
# reinstalling packages that are already present, it does not gate on success.

echo "== TE-001: package audit (cadquery-ocp / vtk must be absent) =="
"${POC_PYTHON}" -m pip list
"${POC_PYTHON}" -m pip show cadquery
"${POC_PYTHON}" -m pip show cadquery-ocp-novtk
if "${POC_PYTHON}" -m pip show cadquery-ocp >/dev/null 2>&1; then
  echo "cadquery-ocp is installed in ${POC_VENV} — this must not happen" >&2
  exit 1
fi
if "${POC_PYTHON}" -m pip show vtk >/dev/null 2>&1; then
  echo "vtk is installed in ${POC_VENV} — this must not happen" >&2
  exit 1
fi
"${POC_PYTHON}" -m pip check || true  # expected metadata-naming mismatch, see Experiment.md

echo "== TE-001: running full evidence collection =="
mkdir -p "${REPORT_DIR}"
python3.13 tools/poc/novtk/te001_run_all.py || true  # non-PASS exit code is a valid TE-001 result

echo "== TE-001: running PoC test suite (against the productive .venv, read-only) =="
if [ -x ".venv/bin/python" ]; then
  TEST_PYTHON=".venv/bin/python"
else
  TEST_PYTHON="python3.13"
fi
"${TEST_PYTHON}" -m pytest tests/poc/novtk/ -v

echo "== TE-001: ruff check =="
"${TEST_PYTHON}" -m ruff check tools/poc/novtk tests/poc/novtk

echo "== TE-001: ruff format check =="
"${TEST_PYTHON}" -m ruff format --check tools/poc/novtk tests/poc/novtk

echo "== TE-001: Gate A result =="
GATE_A_VERDICT=$(python3.13 -c "
import json
with open('${REPORT_DIR}/te001-full-evidence.json') as f:
    data = json.load(f)
print(data['gate_a']['verdict'])
")

echo "TE-001 No-VTK evaluation completed."
if [ "${GATE_A_VERDICT}" = "PASS" ]; then
  echo "Gate A: PASS"
else
  echo "Gate A: ${GATE_A_VERDICT}"
fi
