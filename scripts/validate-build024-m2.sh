#!/usr/bin/env bash
# Build 024 / Milestone 2 — Native Save Dialog & Export Controls validation
# gate.
#
# Re-verifies Build 022's and Build 023's own architecture-conformance
# invariants directly (not via a blind call to validate-build022.sh /
# validate-build023.sh / validate-build024-m1.sh) for the same reason
# validate-build024-m1.sh already established: those scripts encode a frozen
# "unchanged since this build's own baseline" check for
# desktop/src-tauri/src/, desktop/frontend/src/parameter_panel.ts, and the
# WebView capability list, all of which M1 and now M2 legitimately touch
# (see docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md and
# docs/migration/BUILD-024-M2-EXPORT-CONTROLS.md). Never touches
# experiments/te002-tauri or the legacy PySide6 app.
#
# Post-Human-Validation bugfix (see docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md):
# the version of this script that first reported PASS did not catch a real
# `missing required key outputDirectory` runtime defect at the WebView
# invoke() -> Tauri command argument-binding boundary, because nothing in
# the prior gate dispatched a real IPC request through that exact layer —
# the frontend suite mocks invoke() itself, and the packaging smoke test
# talks to the sidecar binary's stdin/stdout directly, bypassing Rust
# entirely. The "Rust — real IPC argument-binding regression" section below
# closes that gap.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build024-m2"
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
  echo "# BUILD-024-M2: $1"
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
check "M2 export controls record present" \
  '[ -f docs/migration/BUILD-024-M2-EXPORT-CONTROLS.md ]'
check "M2 human validation checklist present" \
  '[ -f docs/migration/BUILD-024-M2-HUMAN-VALIDATION.md ]'
check "M1 export foundation record present (baseline)" \
  '[ -f docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md ]'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorodcad/export.py src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorodcad/export.py src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — export / sidecar / preflight unit tests"
"${PY}" -m pytest \
  tests/test_export.py \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  -v

section "Python — real subprocess preflight/overwrite sequence (TE-001.1-patched, VTK-free interpreter)"
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

section "Rust — real IPC argument-binding regression (Build 024 M2 bugfix, see BUILD-024-M2-EXPORT-BUGFIX.md)"
# This is the specific gap that let the original 'missing required key
# outputDirectory' defect reach Human Validation while this whole script
# still reported PASS: the frontend suite mocks @tauri-apps/api/core's
# invoke() entirely (so it only proves what our TypeScript SENDS, never what
# Tauri's generated command deserializer ACTUALLY ACCEPTS), and the
# packaging smoke test below drives the real sidecar binary's stdin/stdout
# DIRECTLY — it never goes through the Rust/Tauri command layer at all, so
# it could never have caught an argument-binding mismatch at that layer.
# commands.rs's ipc_argument_binding tests (run above as part of `cargo
# test`) are the only check that dispatches a real IPC request through
# Tauri's actual generated deserializer (tauri::test::get_ipc_response) —
# assert they actually ran, not just that `cargo test` as a whole passed
# (which would also pass if the module were accidentally excluded).
check "ipc_argument_binding regression tests actually ran (not silently excluded)" \
  'grep -q "commands::tests::ipc_argument_binding::accepts_the_exact_payload_export_ts_sends_for_preflight_and_export ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::rejects_camel_case_output_directory ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::rejects_a_missing_output_directory ... ok" "'"${RUST_TEST_LOG}"'"'
check "engine_export uses rename_all = snake_case (matches export.ts's output_directory key)" \
  'grep -B3 "pub async fn engine_export(" desktop/src-tauri/src/commands.rs | grep -q "rename_all = \"snake_case\""'
check "engine_export_preflight uses rename_all = snake_case (matches export.ts's output_directory key)" \
  'grep -B3 "pub async fn engine_export_preflight(" desktop/src-tauri/src/commands.rs | grep -q "rename_all = \"snake_case\""'
check "export.ts's invoke() payloads use the output_directory (snake_case) key, matching commands.rs's rename_all = snake_case" \
  '[ "$(grep -c "output_directory: outputDirectory" desktop/frontend/src/export.ts)" -eq 2 ]'

section "Frontend — vitest / TypeScript / build"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

section "Export UI — control exists, sources accepted state, isolated from parameter state"
check "export_panel.ts module exists" \
  '[ -f desktop/frontend/src/export_panel.ts ]'
check "export_panel.ts exports createExportPanelController" \
  'grep -q "export function createExportPanelController" desktop/frontend/src/export_panel.ts'
check "export trigger sources getAcceptedRequest(), never a draft" \
  'grep -q "io.getAcceptedRequest()" desktop/frontend/src/export_panel.ts'
check "export_panel.ts never imports parameter_state.ts (isolated concern, no draft access)" \
  '! grep -q "from \"./parameter_state\"" desktop/frontend/src/export_panel.ts'
check "export trigger disabled while live preview is pending/updating" \
  'grep -q "up-to-date.*||.*status === \"error\"" desktop/frontend/src/export_panel.ts'
check "main.ts wires the export panel to the parameter panel via IO, not shared mutable state" \
  'grep -q "createExportPanelController(exportPanelEl" desktop/frontend/src/main.ts'

section "Dialog cancellation and directory-path handling"
check "cancellation (null) is handled as idle, not an error" \
  'grep -q "directory === null" desktop/frontend/src/export_panel.ts'
check "the selected directory path is forwarded to preflight/export unmodified" \
  'grep -q "requestExportPreflight(accepted.values, directory)" desktop/frontend/src/export_panel.ts'

section "Overwrite preflight — backend-driven, no directory enumeration to the frontend"
check "export_preflight sidecar command registered" \
  'grep -q "\"export_preflight\": _run_export_preflight_command" src/zerorod_sidecar/main.py'
check "preflight reuses expected_output_filenames (no duplicated sanitization)" \
  'grep -q "from zerorodcad.export import expected_output_filenames" src/zerorod_sidecar/main.py'
check "engine_export_preflight Rust command registered" \
  'grep -q "pub async fn engine_export_preflight" desktop/src-tauri/src/commands.rs'
check "engine_export_preflight registered in the Tauri invoke handler" \
  'grep -q "commands::engine_export_preflight" desktop/src-tauri/src/lib.rs'
check "confirm_overwrite state offers Cancel/Replace, not silent overwrite" \
  'grep -q "cancel-overwrite" desktop/frontend/src/export_panel.ts && grep -q "confirm-overwrite" desktop/frontend/src/export_panel.ts'

section "Security invariants — WebView capability delta is still exactly the M1 narrow dialog grant"
check "capability grants core:default + dialog:allow-open only (no fs:*, no shell:*, no process:*)" \
  'grep -q "\"permissions\": \[\"core:default\", \"dialog:allow-open\"\]" desktop/src-tauri/capabilities/main-capability.json'
check "no fs:* permission granted to the WebView" \
  '! grep -q "\"fs:" desktop/src-tauri/capabilities/main-capability.json'
check "no shell/process capability exposed to the WebView beyond core:default" \
  '! grep -q "shell:allow\|process:allow" desktop/src-tauri/capabilities/main-capability.json'
check "no dialog:allow-save/message/ask/confirm granted (overwrite confirmation is in-panel UI, not a native dialog)" \
  '! grep -qE "dialog:(allow-save|allow-message|allow-ask|allow-confirm|default)" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP unchanged" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'
check "request timeout unchanged (30s, evidence-based only)" \
  'grep -q "REQUEST_TIMEOUT_SECS: u64 = 30" desktop/src-tauri/src/engine.rs'

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

section "Packaging — productive onedir sidecar rebuild + fresh release .app (best-effort; see docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md Known limitations #1)"
# NOTE (Build 024 M2 bugfix): the smoke test below writes JSON request lines
# directly to the sidecar binary's own stdin and reads its stdout — it
# never goes through the WebView invoke() -> Tauri command -> engine::request
# path at all, so it CANNOT catch an argument-binding mismatch at the
# Rust/Tauri IPC layer (which is exactly what the original 'missing required
# key outputDirectory' defect was). That layer is covered above, by the
# "Rust — real IPC argument-binding regression" section. This smoke test's
# job is proving the Python sidecar side of export/preflight is real and
# correct, not the IPC boundary.
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
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"b\",\"command\":\"export_preflight\",\"parameters\":{\"output_directory\":\"$(pwd)/${EXPORT_SMOKE_DIR}\"}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"c\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${EXPORT_SMOKE_DIR}\"}}" \
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
assert responses["b"]["result"]["has_conflicts"] is False, responses["b"]
assert responses["c"]["ok"] is True, responses["c"]
assert responses["stop"]["ok"] is True, responses["stop"]
files = responses["c"]["result"]["files"]
assert len(files) == 3, files
for entry in files:
    p = Path(entry["path"])
    assert p.is_file() and p.stat().st_size > 0, entry
print("bundled sidecar: preview ok, preflight (no conflict) ok, export produced 3 non-empty files, shutdown ok")
PYEOF
    then
      echo "OK   bundled sidecar smoke-tested through the real onedir binary (preview + export_preflight + export + shutdown)"
    else
      echo "  FAIL bundled sidecar smoke test did not pass" >&2
      FAILED=1
    fi
    rm -rf "${EXPORT_SMOKE_DIR}"

    echo "== building fresh release .app from this M2 HEAD =="
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
  echo "BUILD-024-M2 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-024-M2 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
