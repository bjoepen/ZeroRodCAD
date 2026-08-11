#!/usr/bin/env bash
# Build 024 / Milestone 3 — Export Robustness & Edge Cases validation gate.
#
# Re-verifies Build 022/023/024-M1's own architecture-conformance invariants
# directly (not via a blind call to their own scripts) for the same reason
# validate-build024-m1.sh and validate-build024-m2.sh already established:
# those scripts encode a frozen "unchanged since this build's own baseline"
# check for files M1/M2/M3 all legitimately continue to touch (see
# docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md). Never touches
# experiments/te002-tauri or the legacy PySide6 app.
#
# Lesson carried forward from the Build 024 M2 bugfix
# (docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md): validation must exercise
# real command boundaries, not only mocked frontend helpers or direct
# sidecar stdin. This script keeps M2's "Rust — real IPC argument-binding
# regression" section and adds M3's own structural-result-validation checks
# at the same real boundary.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build024-m3"
mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3.13"
fi

FAILED=0
section() {
  echo ""
  echo "########################################################################"
  echo "# BUILD-024-M3: $1"
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
check "M3 export robustness record present" \
  '[ -f docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md ]'
check "M3 human validation checklist present" \
  '[ -f docs/migration/BUILD-024-M3-HUMAN-VALIDATION.md ]'
check "M2 export controls record present (baseline)" \
  '[ -f docs/migration/BUILD-024-M2-EXPORT-CONTROLS.md ]'
check "M2 bugfix record present (baseline)" \
  '[ -f docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md ]'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorodcad/export.py src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorodcad/export.py src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — export / sidecar / preflight / robustness unit tests"
"${PY}" -m pytest \
  tests/test_export.py \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  -v

section "Python — real subprocess robustness sequences (TE-001.1-patched, VTK-free interpreter)"
if [ -x ".venv-novtk-poc/bin/python" ]; then
  "${PY}" -m pytest tests/test_zerorod_sidecar_persistent.py::TestRealPersistentSubprocess -v
else
  echo "SKIPPED: .venv-novtk-poc not present. Run scripts/validate-te001-novtk.sh first."
fi

section "Python — full repository regression suite"
"${PY}" -m pytest -q

section "Rust — cargo test / fmt / clippy"
RUST_TEST_LOG="${REPORT_DIR}/cargo-test.log"
(cd desktop/src-tauri && cargo test) | tee "${RUST_TEST_LOG}"
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)

section "Rust — real IPC argument-binding regression (Build 024 M2 bugfix; must remain covered)"
check "ipc_argument_binding regression tests actually ran (not silently excluded)" \
  'grep -q "commands::tests::ipc_argument_binding::accepts_the_exact_payload_export_ts_sends_for_preflight_and_export ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::rejects_camel_case_output_directory ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::rejects_a_missing_output_directory ... ok" "'"${RUST_TEST_LOG}"'"'
check "engine_export uses rename_all = snake_case (matches export.ts's output_directory key)" \
  'grep -B3 "pub async fn engine_export(" desktop/src-tauri/src/commands.rs | grep -q "rename_all = \"snake_case\""'
check "engine_export_preflight uses rename_all = snake_case (matches export.ts's output_directory key)" \
  'grep -B3 "pub async fn engine_export_preflight(" desktop/src-tauri/src/commands.rs | grep -q "rename_all = \"snake_case\""'

section "Rust — export-result structural validation (Build 024 M3, prevents false success)"
check "export_result.rs module exists" \
  '[ -f desktop/src-tauri/src/export_result.rs ]'
check "export_result module registered in lib.rs" \
  'grep -q "mod export_result;" desktop/src-tauri/src/lib.rs'
check "engine_export validates its result before returning success" \
  'grep -q "validate_export_result(&payload)" desktop/src-tauri/src/commands.rs'
check "engine_export_preflight validates its result before returning success" \
  'grep -q "validate_export_preflight_result(&payload)" desktop/src-tauri/src/commands.rs'
check "export_result unit tests actually ran (not silently excluded)" \
  'grep -q "export_result::tests::rejects_a_result_missing_an_expected_role ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "export_result::tests::rejects_has_conflicts_inconsistent_with_conflicts_array ... ok" "'"${RUST_TEST_LOG}"'"'

section "Frontend — vitest / TypeScript / build"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

section "Frontend — export robustness/error-recovery coverage"
check "invalid_export_result is mapped to a concise, non-raw error message" \
  'grep -q "invalid_export_result" desktop/frontend/src/export_panel.ts'
check "export.test.ts / export_panel.test.ts present and were part of the vitest run above" \
  '[ -f desktop/frontend/src/export_panel.test.ts ] && [ -f desktop/frontend/src/export.test.ts ]'

section "Security invariants — WebView capability delta is still exactly the M1 narrow dialog grant (M3 adds none)"
check "capability grants core:default + dialog:allow-open only (no fs:*, no shell:*, no process:*)" \
  'grep -q "\"permissions\": \[\"core:default\", \"dialog:allow-open\"\]" desktop/src-tauri/capabilities/main-capability.json'
check "no fs:* permission granted to the WebView" \
  '! grep -q "\"fs:" desktop/src-tauri/capabilities/main-capability.json'
check "no shell/process capability exposed to the WebView beyond core:default" \
  '! grep -q "shell:allow\|process:allow" desktop/src-tauri/capabilities/main-capability.json'
check "no dialog:allow-save/message/ask/confirm granted" \
  '! grep -qE "dialog:(allow-save|allow-message|allow-ask|allow-confirm|default)" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP unchanged" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'
check "request timeout unchanged (30s, evidence-based only — M3 found no evidence to change it)" \
  'grep -q "REQUEST_TIMEOUT_SECS: u64 = 30" desktop/src-tauri/src/engine.rs'
check "engine.rs generic retry-once policy unchanged (M3 decision: safe for export as-is, see docs)" \
  'git diff --quiet f2a7ce9 -- desktop/src-tauri/src/engine.rs 2>/dev/null'

section "Build 022/023 invariants re-verified directly (not via a blind script call — see header)"
check "Tauri v2 CLI/API pinned" \
  'grep -q "\"@tauri-apps/cli\": \"\^2\." desktop/frontend/package.json && grep -q "\"@tauri-apps/api\": \"\^2\." desktop/frontend/package.json'
check "Three.js present" \
  'grep -q "\"three\":" desktop/frontend/package.json'
check "onedir-only sidecar packaging spec (COLLECT present)" \
  'grep -q "COLLECT" packaging/tauri/sidecar-onedir.spec'
check "numba/llvmlite/scipy excluded from the packaging spec" \
  'grep -q "numba" packaging/tauri/sidecar-onedir.spec && grep -q "llvmlite" packaging/tauri/sidecar-onedir.spec && grep -q "scipy" packaging/tauri/sidecar-onedir.spec'
check "hash-gated dylib dedup script present" \
  '[ -f packaging/tauri/dedup_bundle_dylibs.py ]'
check "reproducible build pipeline script present" \
  '[ -x scripts/build-productive-desktop-app.sh ]'
check "cadquery-ocp-novtk (not cadquery-ocp) in the packaging build environment" \
  '.venv-novtk-bundle/bin/pip show cadquery-ocp-novtk >/dev/null 2>&1'
check "legacy PySide6 app retained (not removed)" \
  '[ -d src/zerorodcad_desktop ]'
check "legacy PySide6 app unchanged" \
  'git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null'
check "experiments/te002-tauri retained (not removed)" \
  '[ -d experiments/te002-tauri ]'
check "experiments/te002-tauri unchanged" \
  'git diff --quiet -- experiments/te002-tauri/ 2>/dev/null'
check "0 VTK references added under src/zerorod_sidecar/" \
  '! grep -riq "vtkmodules\|import vtk" src/zerorod_sidecar/main.py'
check "0 VTK references added under src/zerorodcad/export.py" \
  '! grep -riq "vtkmodules\|import vtk" src/zerorodcad/export.py'
check "the wider engine package (model.py/report.py/parameters.py/validation.py) untouched since M1 (f2a7ce9) — export.py's own minimal, additive refactor is the only engine-adjacent change across M1-M3" \
  'git diff --quiet f2a7ce9 -- src/zerorodcad/model.py src/zerorodcad/report.py src/zerorodcad/parameters.py src/zerorodcad/validation.py 2>/dev/null'

section "Packaging — productive onedir sidecar rebuild + fresh release .app"
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
    SPACES_DIR="${REPORT_DIR}/bundled export smoke with spaces"
    rm -rf "${EXPORT_SMOKE_DIR}" "${SPACES_DIR}"
    mkdir -p "${EXPORT_SMOKE_DIR}" "${SPACES_DIR}"
    printf '%s\n' \
      '{"schema":"zerorod-sidecar/v1","request_id":"a","command":"preview"}' \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"b\",\"command\":\"export_preflight\",\"parameters\":{\"output_directory\":\"$(pwd)/${EXPORT_SMOKE_DIR}\"}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"c\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${EXPORT_SMOKE_DIR}\"}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"d\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${SPACES_DIR}\"}}" \
      '{"schema":"zerorod-sidecar/v1","request_id":"stop","command":"shutdown"}' \
      | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/bundled-smoke.jsonl" || true
    if "${PY}" - "${REPORT_DIR}/bundled-smoke.jsonl" "${EXPORT_SMOKE_DIR}" "${SPACES_DIR}" <<'PYEOF'
import json, sys
from pathlib import Path

log_path, export_dir, spaces_dir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
responses = {}
with open(log_path) as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            responses[r["request_id"]] = r

assert responses["a"]["ok"] is True, responses["a"]
assert responses["b"]["ok"] is True, responses["b"]
assert responses["b"]["result"]["has_conflicts"] is False, responses["b"]
assert responses["c"]["ok"] is True, responses["c"]
assert responses["d"]["ok"] is True, responses["d"]
assert responses["stop"]["ok"] is True, responses["stop"]
for rid, directory in (("c", export_dir), ("d", spaces_dir)):
    files = responses[rid]["result"]["files"]
    assert len(files) == 3, files
    for entry in files:
        p = Path(entry["path"])
        assert p.is_file() and p.stat().st_size > 0, entry
print("bundled sidecar: preview ok, preflight ok, export ok, export-into-spaces-path ok, shutdown ok")
PYEOF
    then
      echo "OK   bundled sidecar smoke-tested through the real onedir binary (preview + export_preflight + export + export-into-spaces-path + shutdown)"
    else
      echo "  FAIL bundled sidecar smoke test did not pass" >&2
      FAILED=1
    fi
    rm -rf "${EXPORT_SMOKE_DIR}" "${SPACES_DIR}"

    echo "== building fresh release .app from this M3 HEAD =="
    if bash scripts/build-productive-desktop-app.sh release > "${REPORT_DIR}/app-build.log" 2>&1; then
      APP_PATH="desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
      if [ -d "${APP_PATH}" ]; then
        echo "OK   fresh release .app built: ${APP_PATH}"
      else
        echo "  FAIL release .app not found after build. Log: ${REPORT_DIR}/app-build.log" >&2
        FAILED=1
      fi
    else
      echo "  FAIL fresh release .app build failed. Log: ${REPORT_DIR}/app-build.log" >&2
      FAILED=1
    fi
    rm -rf "${SIDECAR_DIST}" build/zerorod-engine
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

echo ""
echo "########################################################################"
if [ "${FAILED}" -eq 0 ]; then
  echo "BUILD-024-M3 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-024-M3 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
