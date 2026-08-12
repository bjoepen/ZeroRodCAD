#!/usr/bin/env bash
# TE-002.1 sidecar runtime strategy validation. Never touches the productive
# .venv or the existing PySide6 desktop app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/te0021-sidecar-runtime"
POC_ROOT="experiments/te002-tauri"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"

echo "== TE-002.1: verifying Python 3.13 =="
if ! command -v python3.13 >/dev/null 2>&1; then
  echo "python3.13 not found on PATH" >&2
  exit 1
fi
python3.13 -c "import sys; assert sys.version_info[:2] == (3, 13), sys.version"

mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  TEST_PYTHON=".venv/bin/python"
else
  TEST_PYTHON="python3.13"
fi

echo "== TE-002.1: Python sidecar unit/integration tests (one-shot + persistent) =="
"${TEST_PYTHON}" -m pytest tests/poc/tauri/ -v

echo "== TE-002.1: no-VTK / no-PySide6 check in the sidecar's build environment =="
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

echo "== TE-002.1: persistent-mode smoke test against the onedir sidecar (real ZeroRod model) =="
ONEDIR_BIN="${POC_ROOT}/onedir-dist/zerorod-engine/zerorod-engine"
if [ -x "${ONEDIR_BIN}" ]; then
  "${TEST_PYTHON}" - "${ONEDIR_BIN}" "${REPORT_DIR}" <<'PY'
import json
import subprocess
import sys

binary, report_dir = sys.argv[1], sys.argv[2]
proc = subprocess.Popen(
    [binary, "--persistent"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
)


def send(command, request_id):
    req = json.dumps(
        {"schema": "zerorod-sidecar/v1", "request_id": request_id, "command": command, "parameters": {}}
    )
    proc.stdin.write(req + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


resp = send("preview", "validate-1")
assert resp["ok"] is True, resp
meshes = resp["result"]["meshes"]
assert len(meshes) > 0, "no meshes in response"
with open(f"{report_dir}/smoke-response.json", "w") as f:
    json.dump(resp, f)
print("persistent smoke test OK:", [(m["name"], len(m["positions"]) // 3) for m in meshes])

shutdown_resp = send("shutdown", "validate-2")
assert shutdown_resp["ok"] is True, shutdown_resp
assert proc.wait(timeout=5) == 0
print("persistent shutdown OK, exit code 0")
PY

  echo "0 vtk/PySide6 strings check (onedir sidecar binary):"
  vtk_count=$(strings "${ONEDIR_BIN}" 2>/dev/null | grep -ci "vtkmodules" || true)
  pyside_count=$(strings "${ONEDIR_BIN}" 2>/dev/null | grep -ci "PySide6" || true)
  echo "vtkmodules string occurrences: ${vtk_count}"
  echo "PySide6 string occurrences: ${pyside_count}"
  if [ "${vtk_count}" != "0" ] || [ "${pyside_count}" != "0" ]; then
    echo "VTK or PySide6 strings found in sidecar binary — this must not happen" >&2
    exit 1
  fi
else
  echo "NOTE: onedir sidecar binary not built — run tools/poc/tauri/sidecar-onedir.spec via PyInstaller first" >&2
fi

echo "== TE-002.1: Rust tests (engine manager, sidecar, onedir integration) =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo test)
else
  echo "cargo not found — skipping Rust tests" >&2
fi

echo "== TE-002.1: frontend tests =="
if [ -d "${POC_ROOT}/frontend/node_modules" ]; then
  (cd "${POC_ROOT}/frontend" && npm run test -- --run)
else
  echo "NOTE: frontend node_modules not installed — run npm install in ${POC_ROOT}/frontend first" >&2
fi

echo "== TE-002.1: Tauri build check (cargo check, does not launch a window) =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo check)
fi

echo "== TE-002.1: built .app bundle static VTK/PySide6/Qt scan (if built) =="
APP_BUNDLE="${POC_ROOT}/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app"
if [ -d "${APP_BUNDLE}" ]; then
  hits=$(find "${APP_BUNDLE}" \( -iname "*vtk*" -o -iname "*IVtk*" -o -iname "*PySide*" -o -iname "*Qt*" \) | wc -l | tr -d ' ')
  echo "matches: ${hits}"
  if [ "${hits}" != "0" ]; then
    echo "VTK/PySide6/Qt files found in the built app bundle — this must not happen" >&2
    exit 1
  fi
else
  echo "NOTE: app bundle not built — run 'cd ${POC_ROOT}/src-tauri && cargo tauri build' first" >&2
fi

echo "== TE-002.1: ruff (Python sidecar) =="
"${TEST_PYTHON}" -m ruff check tools/poc/tauri tests/poc/tauri
"${TEST_PYTHON}" -m ruff format --check tools/poc/tauri tests/poc/tauri

echo "== TE-002.1: cargo fmt / clippy (Rust) =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo fmt --check)
  (cd "${POC_ROOT}/src-tauri" && cargo clippy --all-targets -- -D warnings)
fi

echo "== TE-002.1: existing ZeroRodCAD test suite (regression check) =="
"${TEST_PYTHON}" -m pytest -q

echo "== TE-002.1: docs presence check =="
for doc in Discovery Runtime-Variants Benchmark-Method Performance Memory Process-Lifecycle \
           Packaging Security Results Conclusion HUMAN-VALIDATION; do
  if [ ! -f "docs/research/TE-002.1-Sidecar-Runtime/${doc}.md" ]; then
    echo "Missing required doc: ${doc}.md" >&2
    exit 1
  fi
done
if [ ! -f "docs/research/TE-002.1-Sidecar-Runtime/ADR-DRAFT-TE0021.md" ]; then
  echo "Missing ADR-DRAFT-TE0021.md" >&2
  exit 1
fi
echo "all required docs present"

echo "TE-002.1 sidecar runtime strategy evaluation completed."
echo "Gate E-A: PASS"
echo "Gate E-B (human validation): PENDING — see docs/research/TE-002.1-Sidecar-Runtime/HUMAN-VALIDATION.md"
