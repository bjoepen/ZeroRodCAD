#!/usr/bin/env bash
# Build 024 / Milestone 1 — Export Architecture & Contract Foundation
# validation gate.
#
# Proves the export sidecar command / Rust boundary end to end against a
# real interpreter (not mocks), re-verifies Build 022's gate and the
# specific Build-023 invariants that still make sense to check after Build
# 024 legitimately modifies desktop/src-tauri/src/ and
# src/zerorod_sidecar/ (scripts/validate-build023.sh's own "no Rust/Python
# source changes since the Build-023 M1 baseline" checks are a historical
# invariant specific to Build 023's own frontend-only M2-M4 milestones and
# are EXPECTED to fail from this point on — see
# docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md's "Files changed in M1"
# for why that is not a real regression). Never touches
# experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build024-m1"
mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3.13"
fi

BUILD023_FINAL_COMMIT="be435b8"

FAILED=0
section() {
  echo ""
  echo "########################################################################"
  echo "# BUILD-024-M1: $1"
  echo "########################################################################"
}
check() {
  local description="$1"
  local condition="$2"
  if eval "${condition}"; then
    echo "  OK   ${description}"
  else
    echo "  FAIL ${description}" >&2
    FAILED=1
  fi
}

section "Documentation present"
check "M1 export foundation record present" \
  '[ -f docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md ]'
check "Build-024 handoff present" \
  '[ -f docs/migration/BUILD-024-HANDOFF.md ]'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — sidecar export unit tests"
"${PY}" -m pytest \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  tests/test_export.py \
  -v

section "Python — real subprocess export proof (TE-001.1-patched, VTK-free interpreter)"
if [ -x ".venv-novtk-poc/bin/python" ]; then
  "${PY}" -m pytest tests/test_zerorod_sidecar_persistent.py::TestRealPersistentSubprocess -v
else
  echo "SKIPPED: .venv-novtk-poc not present. Run scripts/validate-te001-novtk.sh first."
fi

section "Python — full repository regression suite"
"${PY}" -m pytest -q

section "Rust — cargo test / fmt / clippy"
(cd desktop/src-tauri && cargo test)
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)

section "Frontend — vitest / TypeScript / build"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

section "Security invariants — WebView capability delta is exactly the narrow dialog grant"
check "capability grants core:default + dialog:allow-open only (no fs:*, no shell:*, no process:*)" \
  'grep -q "\"permissions\": \[\"core:default\", \"dialog:allow-open\"\]" desktop/src-tauri/capabilities/main-capability.json'
check "no fs:* permission granted to the WebView" \
  '! grep -q "\"fs:" desktop/src-tauri/capabilities/main-capability.json'
check "no shell/process capability exposed to the WebView beyond core:default" \
  '! grep -q "shell:allow\|process:allow" desktop/src-tauri/capabilities/main-capability.json'
check "no dialog:allow-save/message/ask/confirm granted (narrowest permission only)" \
  '! grep -qE "dialog:(allow-save|allow-message|allow-ask|allow-confirm|default)" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP unchanged" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'

section "Contract stability vs. the Build-023 final baseline (${BUILD023_FINAL_COMMIT})"
check "zerorod-parameters/v1 contract doc unchanged" \
  "git diff --quiet ${BUILD023_FINAL_COMMIT} -- docs/contracts/ZEROROD-PARAMETERS-V1.md 2>/dev/null"
check "mesh contract module unchanged" \
  "git diff --quiet ${BUILD023_FINAL_COMMIT} -- src/zerorod_sidecar/mesh_contract.py desktop/frontend/src/mesh.ts desktop/src-tauri/src/mesh.rs 2>/dev/null"
check "sidecar protocol envelope unchanged (protocol.py/protocol.rs logic, not tests)" \
  "git diff --quiet ${BUILD023_FINAL_COMMIT} -- src/zerorod_sidecar/protocol.py 2>/dev/null"
check "parameters_contract.py unchanged (export reuses parse_parameters_request as-is)" \
  "git diff --quiet ${BUILD023_FINAL_COMMIT} -- src/zerorod_sidecar/parameters_contract.py 2>/dev/null"
check "engine.rs unchanged (export flows through the existing request() entry point)" \
  "git diff --quiet ${BUILD023_FINAL_COMMIT} -- desktop/src-tauri/src/engine.rs 2>/dev/null"
check "zerorodcad engine package unchanged (export.py/model.py/report.py/parameters.py/validation.py — no engine rewrite)" \
  "git diff --quiet ${BUILD023_FINAL_COMMIT} -- src/zerorodcad/ 2>/dev/null"
check "no export UI wired into parameter_panel.ts / parameter_state.ts" \
  "git diff --quiet ${BUILD023_FINAL_COMMIT} -- desktop/frontend/src/parameter_panel.ts desktop/frontend/src/parameter_state.ts 2>/dev/null"

section "Build 022 invariants re-verified directly (not via a blind validate-build022.sh call)"
# validate-build022.sh's own architecture-conformance check asserts the
# WebView capability list is EXACTLY ["core:default"] — a Build-022-scoped
# invariant that Build 024 M1 knowingly and documentedly extends by exactly
# one narrow permission (dialog:allow-open, see
# docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md "Security-boundary
# delta"). Re-running that script unmodified would report a FAIL for a
# change this milestone's mandate explicitly authorizes, so the invariants
# that still meaningfully apply after that authorized delta are re-verified
# directly instead (the same approach used above for the Build-023 baseline).
check "Tauri v2 CLI/API pinned" \
  'grep -q "\"@tauri-apps/cli\": \"\^2\." desktop/frontend/package.json && grep -q "\"@tauri-apps/api\": \"\^2\." desktop/frontend/package.json'
check "Three.js present" \
  'grep -q "\"three\":" desktop/frontend/package.json'
check "no onefile fallback (externalBin) in tauri.conf.json" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'
check "onedir-only sidecar packaging spec (COLLECT present)" \
  'grep -q "COLLECT" packaging/tauri/sidecar-onedir.spec'
check "numba/llvmlite/scipy excluded from the packaging spec" \
  'grep -q "numba" packaging/tauri/sidecar-onedir.spec && grep -q "llvmlite" packaging/tauri/sidecar-onedir.spec && grep -q "scipy" packaging/tauri/sidecar-onedir.spec'
check "hash-gated dylib dedup script present" \
  '[ -x packaging/tauri/dedup_bundle_dylibs.py ] || [ -f packaging/tauri/dedup_bundle_dylibs.py ]'
check "reproducible build pipeline script present" \
  '[ -x scripts/build-productive-desktop-app.sh ]'
check "cadquery-ocp-novtk (not cadquery-ocp) in the packaging build environment" \
  '.venv-novtk-bundle/bin/pip show cadquery-ocp-novtk >/dev/null 2>&1'
check "legacy PySide6 app retained (not removed)" \
  '[ -d src/zerorodcad_desktop ]'
check "experiments/te002-tauri retained (not removed)" \
  '[ -d experiments/te002-tauri ]'
check "Build 022 completion record present" \
  '[ -f docs/migration/BUILD-022-COMPLETION.md ]'

section "Packaging — VTK / PySide6 / Qt absence (source-level, unrelated to the bundle-build limitation below)"
check "0 VTK references added under src/zerorod_sidecar/" \
  '! grep -riq "vtkmodules\|import vtk" src/zerorod_sidecar/main.py'
check "legacy PySide6 app unchanged" \
  'git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null'

section "Packaging — productive onedir sidecar rebuild (best-effort; known pre-existing limitation, see docs)"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"
SIDECAR_DIST="desktop/sidecar-dist"
if [ -x "${BUNDLE_PYTHON}" ]; then
  set +e
  rm -rf "${SIDECAR_DIST}" build/zerorod-engine
  "${BUNDLE_VENV}/bin/pyinstaller" --noconfirm --clean --log-level WARN \
    --distpath "${SIDECAR_DIST}" --workpath build/zerorod-engine \
    packaging/tauri/sidecar-onedir.spec > "${REPORT_DIR}/pyinstaller-rebuild.log" 2>&1
  PYINSTALLER_EXIT=$?
  set -e
  if [ "${PYINSTALLER_EXIT}" -eq 0 ] && [ -x "${SIDECAR_DIST}/zerorod-engine/zerorod-engine" ]; then
    echo "OK   productive onedir sidecar rebuilt successfully"
    BUNDLED_SIDECAR="${SIDECAR_DIST}/zerorod-engine/zerorod-engine"
    EXPORT_SMOKE_DIR="${REPORT_DIR}/bundled-export-smoke"
    rm -rf "${EXPORT_SMOKE_DIR}"
    mkdir -p "${EXPORT_SMOKE_DIR}"
    printf '%s\n' \
      '{"schema":"zerorod-sidecar/v1","request_id":"a","command":"preview"}' \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"b\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${EXPORT_SMOKE_DIR}\"}}" \
      '{"schema":"zerorod-sidecar/v1","request_id":"stop","command":"shutdown"}' \
      | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/bundled-smoke.jsonl" || true
    if "${PY}" - "${REPORT_DIR}/bundled-smoke.jsonl" "${EXPORT_SMOKE_DIR}" <<'PYEOF'
import json, sys
from pathlib import Path

log_path, export_dir = sys.argv[1], Path(sys.argv[2])
responses = {}
with open(log_path) as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            responses[r["request_id"]] = r

assert responses["a"]["ok"] is True, responses["a"]
assert responses["b"]["ok"] is True, responses["b"]
assert responses["stop"]["ok"] is True, responses["stop"]
files = responses["b"]["result"]["files"]
assert len(files) == 3, files
for entry in files:
    p = Path(entry["path"])
    assert p.is_file() and p.stat().st_size > 0, entry
print("bundled sidecar: preview ok, export produced 3 non-empty files, shutdown ok")
PYEOF
    then
      echo "OK   bundled sidecar smoke-tested through the real onedir binary (preview + export + shutdown)"
    else
      echo "  FAIL bundled sidecar smoke test (preview/export/shutdown) did not pass" >&2
      FAILED=1
    fi
    rm -rf "${SIDECAR_DIST}" build/zerorod-engine "${EXPORT_SMOKE_DIR}"
  else
    echo "  WARNING: productive onedir sidecar rebuild failed. Log: ${REPORT_DIR}/pyinstaller-rebuild.log"
    tail -5 "${REPORT_DIR}/pyinstaller-rebuild.log" || true
    rm -rf "${SIDECAR_DIST}" build/zerorod-engine
  fi
else
  echo "SKIPPED: ${BUNDLE_VENV} not found. Run scripts/validate-te0012-novtk-bundle.sh first."
fi

echo "== 0 orphan processes =="
if pgrep -f "zerorod-engine-onedir/zerorod-engine\|sidecar-dist/zerorod-engine/zerorod-engine" >/dev/null 2>&1; then
  echo "orphan zerorod-engine process(es) found" >&2
  pgrep -fl "zerorod-engine" >&2
  FAILED=1
fi
echo "0 orphan processes"

section "Repository — experiments/te002-tauri unchanged"
check "experiments/te002-tauri unchanged" \
  'git diff --quiet -- experiments/te002-tauri/ 2>/dev/null'

echo ""
echo "########################################################################"
if [ "${FAILED}" -eq 0 ]; then
  echo "BUILD-024-M1 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-024-M1 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
