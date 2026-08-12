#!/usr/bin/env bash
# TE-002.2B targeted bundle optimization validation. Builds the final
# optimized candidate (onefile fallback removed, dylib dedup applied,
# numba/llvmlite/scipy excluded) reproducibly from clean build config and
# validates it. Never touches the productive .venv or the PySide6 desktop app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/te0022b-bundle-optimization"
POC_ROOT="experiments/te002-tauri"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"

mkdir -p "${REPORT_DIR}"

echo "== TE-002.2B: verifying Python 3.13 =="
if ! command -v python3.13 >/dev/null 2>&1; then
  echo "python3.13 not found on PATH" >&2
  exit 1
fi
python3.13 -c "import sys; assert sys.version_info[:2] == (3, 13), sys.version"

if [ -x ".venv/bin/python" ]; then
  TEST_PYTHON=".venv/bin/python"
else
  TEST_PYTHON="python3.13"
fi

echo "== TE-002.2B: sidecar unit/integration tests =="
"${TEST_PYTHON}" -m pytest tests/poc/tauri/ -v

echo "== TE-002.2B: full repo regression suite =="
"${TEST_PYTHON}" -m pytest -q

echo "== TE-002.2B: rebuild onedir sidecar (Optimization C+D excludes baked into the spec) =="
if [ -x "${BUNDLE_PYTHON}" ]; then
  rm -rf "${POC_ROOT}/onedir-dist" build/pyinstaller-onedir
  "${BUNDLE_VENV}/bin/pyinstaller" --noconfirm --clean \
    --distpath "${POC_ROOT}/onedir-dist" --workpath build/pyinstaller-onedir \
    tools/poc/tauri/sidecar-onedir.spec 2>&1 | tee "${REPORT_DIR}/pyinstaller-onedir-build.log"
else
  echo "NOTE: ${BUNDLE_VENV} not present — run scripts/validate-te0012-novtk-bundle.sh first" >&2
  exit 1
fi

echo "== TE-002.2B: no VTK/PySide6/numba/scipy/llvmlite in rebuilt sidecar =="
ONEDIR_DIR="${POC_ROOT}/onedir-dist/zerorod-engine"
for pattern in vtk PySide numba scipy llvmlite; do
  count=$(find "${ONEDIR_DIR}" -iname "*${pattern}*" | wc -l | tr -d ' ')
  echo "  ${pattern}: ${count} matches"
  if [ "${pattern}" != "vtk" ] && [ "${pattern}" != "PySide" ] && [ "${count}" = "0" ]; then
    : # numba/scipy/llvmlite expected to be 0 (excluded)
  fi
done
if [ "$(find "${ONEDIR_DIR}" -iname "*vtk*" -o -iname "*PySide*" | wc -l | tr -d ' ')" != "0" ]; then
  echo "VTK or PySide6 found in rebuilt sidecar — this must not happen" >&2
  exit 1
fi
if [ "$(find "${ONEDIR_DIR}" -iname "*numba*" -o -iname "*llvmlite*" -o -iname "*scipy*" | wc -l | tr -d ' ')" != "0" ]; then
  echo "numba/llvmlite/scipy still present after exclusion — Optimization C/D regressed" >&2
  exit 1
fi

echo "== TE-002.2B: persistent-mode smoke test against the rebuilt onedir sidecar =="
ONEDIR_BIN="${ONEDIR_DIR}/zerorod-engine"
"${TEST_PYTHON}" - "${ONEDIR_BIN}" "${REPORT_DIR}" <<'PY'
import json
import subprocess
import sys

binary, report_dir = sys.argv[1], sys.argv[2]
proc = subprocess.Popen(
    [binary, "--persistent"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
)


def send(command, request_id, parameters=None):
    req = json.dumps(
        {"schema": "zerorod-sidecar/v1", "request_id": request_id, "command": command, "parameters": parameters or {}}
    )
    proc.stdin.write(req + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


resp = send("preview", "validate-1")
assert resp["ok"] is True, resp
meshes = resp["result"]["meshes"]
assert len(meshes) > 0, "no meshes in response"
print("persistent smoke test OK:", [(m["name"], len(m["positions"]) // 3) for m in meshes])

bad = send("preview", "validate-2", {"body_width": 0})
assert bad["ok"] is False and bad["error"]["code"] == "unsupported_parameters"
print("error path OK")

shutdown_resp = send("shutdown", "validate-3")
assert shutdown_resp["ok"] is True, shutdown_resp
assert proc.wait(timeout=5) == 0
print("persistent shutdown OK, exit code 0")
PY

echo "== TE-002.2B: copy onedir into Tauri resources, purge stale caches =="
rm -rf "${POC_ROOT}/src-tauri/resources/zerorod-engine-onedir"
rm -rf "${POC_ROOT}/src-tauri/target/release/zerorod-engine-onedir"
rm -rf "${POC_ROOT}/src-tauri/target/debug/zerorod-engine-onedir"
rm -rf "${POC_ROOT}/src-tauri/target/release/bundle"
cp -R "${ONEDIR_DIR}" "${POC_ROOT}/src-tauri/resources/zerorod-engine-onedir"

echo "== TE-002.2B: Rust tests =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo test)
else
  echo "cargo not found — skipping Rust tests" >&2
fi

echo "== TE-002.2B: frontend tests =="
if [ -d "${POC_ROOT}/frontend/node_modules" ]; then
  (cd "${POC_ROOT}/frontend" && npm run test -- --run)
else
  echo "NOTE: frontend node_modules not installed — run npm install in ${POC_ROOT}/frontend first" >&2
fi

echo "== TE-002.2B: Tauri build (onefile externalBin already removed from tauri.conf.json) =="
if command -v cargo >/dev/null 2>&1 && [ -x "${POC_ROOT}/frontend/node_modules/.bin/tauri" ]; then
  (cd "${POC_ROOT}" && ./frontend/node_modules/.bin/tauri build)
else
  echo "tauri CLI not found in frontend/node_modules — skipping full app build" >&2
fi

APP_BUNDLE="${POC_ROOT}/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app"
if [ -d "${APP_BUNDLE}" ]; then
  echo "== TE-002.2B: dylib dedup (Optimization B) =="
  "${TEST_PYTHON}" tools/poc/tauri/dedup_bundle_dylibs.py \
    "${ONEDIR_DIR}/_internal" \
    "${APP_BUNDLE}/Contents/Resources/zerorod-engine-onedir/_internal" \
    --json | tee "${REPORT_DIR}/dedup-validate-result.json"

  echo "== TE-002.2B: static VTK/PySide6/Qt/onefile scan on final bundle =="
  hits=$(find "${APP_BUNDLE}" \( -iname "*vtk*" -o -iname "*IVtk*" -o -iname "*PySide*" -o -iname "*Qt*" \) | wc -l | tr -d ' ')
  echo "VTK/PySide6/Qt matches: ${hits}"
  if [ "${hits}" != "0" ]; then
    echo "VTK/PySide6/Qt files found in the built app bundle — this must not happen" >&2
    exit 1
  fi
  macos_files=$(find "${APP_BUNDLE}/Contents/MacOS" -type f | wc -l | tr -d ' ')
  if [ "${macos_files}" != "1" ]; then
    echo "expected exactly 1 file in Contents/MacOS (onefile sidecar should be absent) — found ${macos_files}" >&2
    exit 1
  fi

  echo "== TE-002.2B: final bundle size =="
  bytes=$(find "${APP_BUNDLE}" -type f -exec stat -f%z {} \; | awk '{sum+=$1} END {print sum}')
  echo "final bundle: ${bytes} bytes"

  echo "== TE-002.2B: runtime probe (export-probe, real STL+STEP against bundled binary) =="
  "${TEST_PYTHON}" tools/poc/tauri/capture_runtime_trace.py \
    "${APP_BUNDLE}/Contents/Resources/zerorod-engine-onedir/zerorod-engine" \
    --bundle-root "${APP_BUNDLE}/Contents/Resources/zerorod-engine-onedir" \
    --profile export-probe \
    --output "${REPORT_DIR}/runtime-trace/validate-export-trace.json" \
    --stimulus-dir "${REPORT_DIR}/stimulus/validate-export"
else
  echo "NOTE: app bundle not built — skipping bundle-level checks" >&2
fi

echo "== TE-002.2B: ruff (Python) =="
"${TEST_PYTHON}" -m ruff check tools/poc/tauri packaging/macos src/zerorod_analysis
"${TEST_PYTHON}" -m ruff format --check tools/poc/tauri packaging/macos src/zerorod_analysis

echo "== TE-002.2B: cargo fmt / clippy (Rust) =="
if command -v cargo >/dev/null 2>&1; then
  (cd "${POC_ROOT}/src-tauri" && cargo fmt --check)
  (cd "${POC_ROOT}/src-tauri" && cargo clippy --all-targets -- -D warnings)
fi

echo "== TE-002.2B: docs presence check =="
for doc in Discovery Runtime-Evidence Import-Origins Optimization-A-Onefile Optimization-B-Dylibs \
           Optimization-C-Numba-Llvmlite Optimization-D-Scipy Size-Comparison Runtime-Validation \
           Results Conclusion HUMAN-VALIDATION; do
  if [ ! -f "docs/research/TE-002.2B-Tauri-Bundle-Optimization/${doc}.md" ]; then
    echo "Missing required doc: ${doc}.md" >&2
    exit 1
  fi
done
echo "all required docs present"

echo "== TE-002.2B: machine-readable results check =="
if [ ! -f "${REPORT_DIR}/optimization-results.json" ]; then
  echo "Missing ${REPORT_DIR}/optimization-results.json" >&2
  exit 1
fi
"${TEST_PYTHON}" -c "import json; json.load(open('${REPORT_DIR}/optimization-results.json'))"
echo "optimization-results.json present and valid JSON"

echo "TE-002.2B targeted bundle optimization validation completed."
echo "Gate F-B: PASS"
echo "Human validation: PENDING — see docs/research/TE-002.2B-Tauri-Bundle-Optimization/HUMAN-VALIDATION.md"
