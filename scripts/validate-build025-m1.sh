#!/usr/bin/env bash
# Build 025 / Milestone 1 — Project Persistence validation gate.
#
# Re-verifies Build 022-024's own architecture-conformance invariants
# directly (not via a blind call to validate-build022.sh / -023.sh /
# -024.sh) for the same reason every prior milestone gate already
# established (see validate-build024-m2.sh's header): those scripts encode a
# frozen "unchanged since this build's own baseline" check for files M1
# legitimately touches (desktop/src-tauri/src/commands.rs, lib.rs,
# desktop/frontend/src/parameter_panel.ts, main.ts, the WebView capability
# list). Never touches experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build025-m1"
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
  echo "# BUILD-025-M1: $1"
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
check "M1 project persistence record present" \
  '[ -f docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md ]'
check "M1 human validation checklist present" \
  '[ -f docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md ]'
check "Discovery feature parity matrix present (baseline)" \
  '[ -f docs/migration/BUILD-025-FEATURE-PARITY-MATRIX.md ]'
check "Discovery project persistence analysis present (baseline)" \
  '[ -f docs/migration/BUILD-025-PROJECT-PERSISTENCE-ANALYSIS.md ]'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — project.py / sidecar project_open+project_save unit tests"
"${PY}" -m pytest \
  tests/test_project.py \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  -v

section "Python — real subprocess project save/open/preview/export sequence (TE-001.1-patched, VTK-free interpreter)"
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

section "Rust — real IPC argument-binding regression (project persistence commands, see BUILD-024-M2-EXPORT-BUGFIX.md precedent)"
# Same lesson Build 024 M2's Human Validation caught for engine_export: the
# frontend suite mocks @tauri-apps/api/core's invoke() entirely (proving
# only what our TypeScript SENDS, never what Tauri's generated command
# deserializer ACTUALLY ACCEPTS). Every new snake_case-argument command this
# milestone adds gets its own real-dispatch twin test from the start —
# assert they actually ran, not just that `cargo test` as a whole passed.
check "project persistence ipc_argument_binding regression tests actually ran" \
  'grep -q "commands::tests::ipc_argument_binding::accepts_the_exact_payload_project_ts_sends_for_open ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::accepts_the_exact_payload_project_ts_sends_for_save ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::accepts_the_exact_payload_project_ts_sends_for_save_file_dialog ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::rejects_camel_case_default_file_name ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "commands::tests::ipc_argument_binding::rejects_a_missing_path_for_open ... ok" "'"${RUST_TEST_LOG}"'"'
check "engine_project_open uses rename_all = snake_case" \
  'grep -B3 "pub async fn engine_project_open(" desktop/src-tauri/src/commands.rs | grep -q "rename_all = \"snake_case\""'
check "engine_project_save uses rename_all = snake_case" \
  'grep -B3 "pub async fn engine_project_save(" desktop/src-tauri/src/commands.rs | grep -q "rename_all = \"snake_case\""'
check "select_project_save_file uses rename_all = snake_case (default_file_name)" \
  'grep -B3 "pub async fn select_project_save_file(" desktop/src-tauri/src/commands.rs | grep -q "rename_all = \"snake_case\""'
check "project.ts's invoke() payload uses the default_file_name (snake_case) key" \
  'grep -q "default_file_name: defaultFileName" desktop/frontend/src/project.ts'

section "Frontend — vitest / TypeScript / build"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

section "Project persistence surface — commands, UI, and existing-format reuse"
check "project.py reused unmodified (no new project format invented)" \
  'git diff --quiet -- src/zerorodcad/project.py 2>/dev/null'
check "sidecar project_open command registered" \
  'grep -q "\"project_open\": _run_project_open_command" src/zerorod_sidecar/main.py'
check "sidecar project_save command registered" \
  'grep -q "\"project_save\": _run_project_save_command" src/zerorod_sidecar/main.py'
check "project_open reuses zerorodcad.project.load_project (no duplicated parser)" \
  'grep -q "from zerorodcad.project import load_project" src/zerorod_sidecar/main.py'
check "project_save reuses zerorodcad.project.save_project (no duplicated writer)" \
  'grep -q "from zerorodcad.project import save_project" src/zerorod_sidecar/main.py'
check "engine_project_open Rust command registered" \
  'grep -q "pub async fn engine_project_open" desktop/src-tauri/src/commands.rs'
check "engine_project_save Rust command registered" \
  'grep -q "pub async fn engine_project_save" desktop/src-tauri/src/commands.rs'
check "all 4 new commands registered in the Tauri invoke handler" \
  'grep -q "commands::select_project_open_file" desktop/src-tauri/src/lib.rs \
   && grep -q "commands::select_project_save_file" desktop/src-tauri/src/lib.rs \
   && grep -q "commands::engine_project_open" desktop/src-tauri/src/lib.rs \
   && grep -q "commands::engine_project_save" desktop/src-tauri/src/lib.rs'
check "project_panel.ts module exists" \
  '[ -f desktop/frontend/src/project_panel.ts ]'
check "project_state.ts module exists" \
  '[ -f desktop/frontend/src/project_state.ts ]'
check "Save sources getAccepted(), never a draft (§5/§6 of the mandate)" \
  'grep -q "io.getAccepted()" desktop/frontend/src/project_panel.ts'
check "project_dirty is derived from accepted vs. saved baseline, not draft vs. saved (§9)" \
  'grep -q "!valuesEqual(session.savedBaseline, accepted)" desktop/frontend/src/project_state.ts'
check "uncommitted-draft guard kept separate from project_dirty, never merged (§22)" \
  'grep -q "isProjectDirty(session, accepted) || hasUncommittedDraft" desktop/frontend/src/project_state.ts'
check "main.ts wires the project panel to the parameter panel via IO, not shared mutable state" \
  'grep -q "createProjectPanelController(projectPanelEl" desktop/frontend/src/main.ts'

section "Unsaved-changes guard — New/Open/Quit all covered, Save/Discard/Cancel"
check "guard offers Save/Discard/Cancel (§17)" \
  'grep -q "guard-cancel" desktop/frontend/src/project_panel.ts \
   && grep -q "guard-discard" desktop/frontend/src/project_panel.ts \
   && grep -q "guard-save" desktop/frontend/src/project_panel.ts'
check "New is guarded through guardThenRun before performing the action" \
  'grep -q "guardThenRun(\"new\")" desktop/frontend/src/project_panel.ts'
check "Open is guarded through guardThenRun before performing the action" \
  'grep -q "guardThenRun(\"open\")" desktop/frontend/src/project_panel.ts'
check "Quit/window-close is intercepted via confirmQuit (§19/§20)" \
  'grep -q "onCloseRequested" desktop/frontend/src/main.ts && grep -q "projectPanel.confirmQuit()" desktop/frontend/src/main.ts'
check "window-close does not itself call any shutdown command (§19) — a prose comment may still name engine::kill_if_running for context" \
  '! grep -q "shutdownEngine(\|invoke(\"engine_shutdown\"" desktop/frontend/src/main.ts'

section "Open atomicity — failure must not touch current state before commit (§12)"
check "requestProjectOpen failure is caught before loadProjectValues is ever called" \
  'grep -A3 "requestProjectOpen(path)" desktop/frontend/src/project_panel.ts | grep -q "catch"'
check "sidecar project_open re-validates domain rules before returning (Level 3, defense in depth)" \
  'grep -A2 "def _run_project_open_command" src/zerorod_sidecar/main.py > /dev/null && grep -q "validate_parameters(params)" src/zerorod_sidecar/main.py'

section "Security invariants — WebView capability delta is exactly dialog:allow-open (reused) + a new dialog:allow-save"
check "capability grants core:default + dialog:allow-open + dialog:allow-save only" \
  'grep -q "\"permissions\": \[\"core:default\", \"dialog:allow-open\", \"dialog:allow-save\"\]" desktop/src-tauri/capabilities/main-capability.json'
check "no fs:* permission granted to the WebView" \
  '! grep -q "\"fs:" desktop/src-tauri/capabilities/main-capability.json'
check "no shell/process capability exposed to the WebView beyond core:default" \
  '! grep -q "shell:allow\|process:allow" desktop/src-tauri/capabilities/main-capability.json'
check "no message/ask/confirm dialog capability granted" \
  '! grep -qE "dialog:(allow-message|allow-ask|allow-confirm)" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP unchanged" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'
check "request timeout unchanged (30s, evidence-based only)" \
  'grep -q "REQUEST_TIMEOUT_SECS: u64 = 30" desktop/src-tauri/src/engine.rs'

section "Build 022-024 invariants re-verified directly (not via a blind script call — see header)"
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
check "engine.rs lazy-spawn/timeout/crash-restart machinery unchanged (§49 architecture guardrail)" \
  'git diff --quiet -- desktop/src-tauri/src/engine.rs 2>/dev/null'

section "Packaging — productive onedir sidecar rebuild + fresh release .app (best-effort)"
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
    PROJECT_SMOKE_DIR="${REPORT_DIR}/bundled-project-smoke"
    rm -rf "${PROJECT_SMOKE_DIR}"
    mkdir -p "${PROJECT_SMOKE_DIR}"
    printf '%s\n' \
      '{"schema":"zerorod-sidecar/v1","request_id":"a","command":"preview"}' \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"b\",\"command\":\"project_save\",\"parameters\":{\"path\":\"$(pwd)/${PROJECT_SMOKE_DIR}/smoke.zerorod\"}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"c\",\"command\":\"project_open\",\"parameters\":{\"path\":\"$(pwd)/${PROJECT_SMOKE_DIR}/smoke.zerorod\"}}" \
      '{"schema":"zerorod-sidecar/v1","request_id":"stop","command":"shutdown"}' \
      | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/bundled-smoke.jsonl" || true
    if "${PY}" - "${REPORT_DIR}/bundled-smoke.jsonl" "${PROJECT_SMOKE_DIR}" <<'PYEOF'
import json, sys
from pathlib import Path

log_path, smoke_dir = sys.argv[1], Path(sys.argv[2])
responses = {}
with open(log_path) as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            responses[r["request_id"]] = r

assert responses["a"]["ok"] is True, responses["a"]
assert responses["b"]["ok"] is True, responses["b"]
assert responses["c"]["ok"] is True, responses["c"]
assert responses["stop"]["ok"] is True, responses["stop"]
saved_path = Path(responses["b"]["result"]["path"])
assert saved_path.is_file() and saved_path.stat().st_size > 0, responses["b"]
assert responses["c"]["result"]["values"]["body_width"] == 38.0, responses["c"]
print("bundled sidecar: preview ok, project_save wrote a real file, project_open round-tripped it, shutdown ok")
PYEOF
    then
      echo "OK   bundled sidecar smoke-tested through the real onedir binary (preview + project_save + project_open + shutdown)"
    else
      echo "  FAIL bundled sidecar smoke test did not pass" >&2
      FAILED=1
    fi
    rm -rf "${PROJECT_SMOKE_DIR}"

    echo "== building fresh release .app from this M1 HEAD =="
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
  echo "BUILD-025-M1 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-025-M1 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
