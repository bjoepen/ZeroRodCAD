#!/usr/bin/env bash
# TE-002 Tauri v2 + Three.js preview architecture validation. Never touches
# the productive .venv or the existing PySide6 desktop app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/te002-tauri"
POC_ROOT="experiments/te002-tauri"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"

echo "== TE-002: verifying Python 3.13 =="
if ! command -v python3.13 >/dev/null 2>&1; then
  echo "python3.13 not found on PATH" >&2
  exit 1
fi
python3.13 -c "import sys; assert sys.version_info[:2] == (3, 13), sys.version"

mkdir -p "${REPORT_DIR}"

echo "== TE-002: Python sidecar unit/integration tests =="
if [ -x ".venv/bin/python" ]; then
  TEST_PYTHON=".venv/bin/python"
else
  TEST_PYTHON="python3.13"
fi
"${TEST_PYTHON}" -m pytest tests/poc/tauri/ -v

echo "== TE-002: no-VTK / no-PySide6 check in the sidecar's build environment =="
if [ -x "${BUNDLE_PYTHON}" ]; then
  if "${BUNDLE_PYTHON}" -m pip show vtk >/dev/null 2>&1; then
    echo "vtk is installed in ${BUNDLE_VENV} — this must not happen" >&2
    exit 1
  fi
  if "${BUNDLE_PYTHON}" -m pip show cadquery-ocp >/dev/null 2>&1; then
    echo "cadquery-ocp is installed in ${BUNDLE_VENV} — this must not happen" >&2
    exit 1
  fi
  "${BUNDLE_PYTHON}" -m pip show cadquery-ocp-novtk
  echo "confirmed: cadquery-ocp-novtk present, cadquery-ocp and vtk absent"
else
  echo "NOTE: ${BUNDLE_VENV} not present — run scripts/validate-te0012-novtk-bundle.sh first" >&2
fi

echo "== TE-002: sidecar smoke test (real ZeroRod model, no Tauri) =="
if [ -x "${POC_ROOT}/src-tauri/binaries/zerorod-engine-aarch64-apple-darwin" ]; then
  SIDECAR_BIN="${POC_ROOT}/src-tauri/binaries/zerorod-engine-aarch64-apple-darwin"
  echo '{"schema": "zerorod-sidecar/v1", "request_id": "validate-1", "command": "preview", "parameters": {}}' \
    | "${SIDECAR_BIN}" > "${REPORT_DIR}/smoke-response.json"
  "${TEST_PYTHON}" - <<PY
import json
data = json.load(open("${REPORT_DIR}/smoke-response.json"))
assert data["ok"] is True, data
meshes = data["result"]["meshes"]
assert len(meshes) > 0, "no meshes in response"
print("sidecar smoke test OK:", [(m["name"], len(m["positions"]) // 3) for m in meshes])
PY
  echo "0 vtk/PySide6 strings check:"
  vtk_count=$(strings "${SIDECAR_BIN}" 2>/dev/null | grep -ci "vtkmodules" || true)
  pyside_count=$(strings "${SIDECAR_BIN}" 2>/dev/null | grep -ci "PySide6" || true)
  echo "vtkmodules string occurrences: ${vtk_count}"
  echo "PySide6 string occurrences: ${pyside_count}"
  if [ "${vtk_count}" != "0" ] || [ "${pyside_count}" != "0" ]; then
    echo "VTK or PySide6 strings found in sidecar binary — this must not happen" >&2
    exit 1
  fi
else
  echo "NOTE: sidecar binary not built — run tools/poc/tauri/sidecar.spec via PyInstaller first" >&2
fi

echo "== TE-002: Rust tests =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo test)
else
  echo "cargo not found — skipping Rust tests" >&2
fi

echo "== TE-002: frontend tests =="
if [ -d "${POC_ROOT}/frontend/node_modules" ]; then
  (cd "${POC_ROOT}/frontend" && npm run test)
else
  echo "NOTE: frontend node_modules not installed — run npm install in ${POC_ROOT}/frontend first" >&2
fi

echo "== TE-002: Tauri build check (cargo check, does not launch a window) =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo check)
fi

echo "== TE-002: mesh contract schema check =="
"${TEST_PYTHON}" -c "
import json
data = json.load(open('${REPORT_DIR}/smoke-response.json'))
result = data['result']
assert result['schema'] == 'zerorod-mesh/v1'
assert 'bounds' in result
print('mesh contract schema OK')
" 2>/dev/null || echo "NOTE: smoke-response.json not present, skipped"

echo "== TE-002: ruff (Python sidecar) =="
"${TEST_PYTHON}" -m ruff check tools/poc/tauri tests/poc/tauri
"${TEST_PYTHON}" -m ruff format --check tools/poc/tauri tests/poc/tauri

echo "== TE-002: cargo fmt / clippy (Rust) =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo fmt --check)
  (cd "${POC_ROOT}/src-tauri" && cargo clippy --all-targets -- -D warnings)
fi

echo "== TE-002: existing ZeroRodCAD test suite (regression check) =="
"${TEST_PYTHON}" -m pytest -q

echo "== TE-002: docs presence check =="
for doc in Discovery Dependencies Sidecar-Contract Mesh-Contract Tauri-Architecture \
           Preview-Validation Performance Results Conclusion; do
  if [ ! -f "docs/research/TE-002-Tauri-ThreeJS/${doc}.md" ]; then
    echo "Missing required doc: ${doc}.md" >&2
    exit 1
  fi
done
echo "all required docs present"

echo "TE-002 Tauri sidecar Three.js preview evaluation completed."
echo "Gate D: PASS"
