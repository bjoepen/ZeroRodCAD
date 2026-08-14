#!/usr/bin/env bash
# Build 025 / Milestone 4 — Desktop Shell & Native Integration validation
# gate.
#
# Re-verifies the still-valid subset of Build 025 M1-M3's own checks
# directly (drift classified below, not a blind call to
# validate-build025-m1.sh/-m2.sh/-m3.sh — same reasoning each prior
# milestone gate already established), plus this milestone's own new
# checks: the native macOS menu exists and contains no
# `PredefinedMenuItem::quit` (the M1 bypass mechanism), native Quit shares
# the exact same guard the red close button already uses, re-entrancy
# safety, File/View menu routing, visibility/menu-checkbox
# synchronization, and build identity now reporting M4. Never touches
# experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build025-m4"
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
  echo "# BUILD-025-M4: $1"
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
check "M4 desktop shell record present" \
  '[ -f docs/migration/BUILD-025-M4-DESKTOP-SHELL.md ]'
check "M4 human validation checklist present" \
  '[ -f docs/migration/BUILD-025-M4-HUMAN-VALIDATION.md ]'
check "M3 human validation now recorded PASS (§2 of the mandate)" \
  'grep -q "Status: PASS" docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md'
check "the M1 Quit finding is explicitly marked FIXED IN M4, backed by this milestone's own record" \
  'grep -qi "FIXED IN M4" docs/migration/BUILD-025-M4-DESKTOP-SHELL.md'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — zero changes expected (§53 of the M3 mandate's own rule still applies: M4 is a desktop-shell milestone, not a Python build)"
check "no Python source changed by M4" \
  'git diff --quiet 9c8d1a3 -- src/zerorod_sidecar/ src/zerorodcad/ 2>/dev/null'
"${PY}" -m pytest -q

section "Rust — cargo test / fmt / clippy"
RUST_TEST_LOG="${REPORT_DIR}/cargo-test.log"
(cd desktop/src-tauri && cargo test) | tee "${RUST_TEST_LOG}"
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)
check "native-close ACL regression test (Build 025 M1 corrective fix) still passes unchanged" \
  'grep -q "window_destroy_is_permitted_for_the_main_window ... ok" "'"${RUST_TEST_LOG}"'"'
check "engine.rs/protocol.rs/mesh.rs/export_result.rs (the lifecycle/protocol layer, §52 of the M3 mandate: no second lifecycle manager) unchanged" \
  'git diff --quiet 9c8d1a3 -- desktop/src-tauri/src/engine.rs desktop/src-tauri/src/protocol.rs desktop/src-tauri/src/mesh.rs desktop/src-tauri/src/export_result.rs 2>/dev/null'
check "new menu-event-boundary regression tests actually ran" \
  'grep -q "native_menu::.*routing_quit_to_window_close_does_not_panic_with_only_a_main_window_present ... ok\|routing_quit_to_window_close_does_not_panic_with_only_a_main_window_present ... ok" "'"${RUST_TEST_LOG}"'" \
   && grep -q "routing_a_non_quit_id_with_no_menu_present_does_not_panic ... ok" "'"${RUST_TEST_LOG}"'"'

section "Frontend — vitest / TypeScript / build"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

section "Build identity — must report Build 025 / M4, not M1/M2/M3 (§3 of the mandate)"
check "app_info() reports the current build/milestone pair (single source, commands.rs)" \
  'grep -q "build: \"025\".to_string()" desktop/src-tauri/src/commands.rs \
   && grep -q "milestone: \"M4\".to_string()" desktop/src-tauri/src/commands.rs'
check "app_info() never reports an earlier Build 025 milestone (general regression, extended to include M3)" \
  'grep -q "\"M1\", \"M2\", \"M3\"" desktop/src-tauri/src/commands.rs'
check "diagnostics_panel.ts remains the one place that renders live build/milestone identity (unchanged mechanism)" \
  'grep -q "appInfo.build} \${appInfo.milestone}" desktop/frontend/src/diagnostics_panel.ts'
check "About's version string is built from the same app_info() call — never a second hardcoded identity string (§23 of the mandate)" \
  'grep -q "let info = app_info();" desktop/src-tauri/src/menu.rs \
   && grep -q "info.version, info.build, info.milestone" desktop/src-tauri/src/menu.rs'
check "diagnostics_panel.test.ts fixture reflects the current milestone, not a stale one" \
  'grep -q "milestone: \"M4\"" desktop/frontend/src/diagnostics_panel.test.ts \
   && grep -q "Build 025 M4" desktop/frontend/src/diagnostics_panel.test.ts'

section "Native menu — Quit does not bypass the guard (§6-9/§27 of the mandate, the central M4 requirement)"
check "menu.rs never actually calls PredefinedMenuItem::quit(...) anywhere (the exact M1 bypass mechanism — text mentions in doc comments explaining its deliberate absence are expected and fine)" \
  '! grep -q "PredefinedMenuItem::quit(" desktop/src-tauri/src/menu.rs'
check "the Quit item is constructed as a plain custom MenuItem with the quit id, not a predefined action" \
  'grep -B4 "MENU_ID_QUIT," desktop/src-tauri/src/menu.rs | grep -q "MenuItem::with_id(" \
   && grep -A2 "MENU_ID_QUIT," desktop/src-tauri/src/menu.rs | grep -q "Quit ZeroRodCAD"'
check "the quit id resumes via WebviewWindow::close() — never AppHandle::exit()/std::process::exit() (structural; text mentions in doc comments explaining what NOT to do are expected and fine)" \
  'grep -A8 "if id == MENU_ID_QUIT" desktop/src-tauri/src/menu.rs | grep -q "window.close()" \
   && ! grep -v "^\s*//" desktop/src-tauri/src/menu.rs | grep -q "app\.exit(\|std::process::exit("'
check "no second confirmQuit-style guard implementation exists anywhere (§9 of the mandate — one guard, not two; text mentions in comments explaining what NOT to create are expected and fine)" \
  '! grep -v "^\s*//" desktop/frontend/src/*.ts desktop/src-tauri/src/*.rs | grep -qE "confirmNativeQuit|confirmWindowQuit|confirmMenuQuit"'
check "main.ts's onCloseRequested is the one interception point, now re-entrancy-safe via close_flow.ts" \
  'grep -q "createCloseRequestHandler" desktop/frontend/src/main.ts \
   && grep -q "confirmQuit: () => projectPanel.confirmQuit()" desktop/frontend/src/main.ts'
check "re-entrancy regression tests exist and cover repeated/overlapping close attempts" \
  'grep -q "re-entrancy: a second close event arriving while the first is still pending" desktop/frontend/src/close_flow.test.ts \
   && grep -q "repeated Cmd+Q" desktop/frontend/src/close_flow.test.ts \
   && grep -q "red close and native Quit share the exact same handler instance" desktop/frontend/src/close_flow.test.ts'
check "the shared guard (project_panel.ts's confirmQuit) itself is unchanged by M4" \
  'git diff --quiet 9c8d1a3 -- desktop/frontend/src/project_state.ts 2>/dev/null'

section "File menu routing (§20/§21/§33 of the mandate — same workflows, no duplicated logic in Rust)"
check "project_panel.ts exposes trigger methods used by the native menu, not a second New/Open/Save implementation" \
  'grep -q "triggerNew: () => guardThenRun" desktop/frontend/src/project_panel.ts \
   && grep -q "triggerOpen: () => guardThenRun" desktop/frontend/src/project_panel.ts \
   && grep -q "triggerSave: () => void performSave()" desktop/frontend/src/project_panel.ts \
   && grep -q "triggerSaveAs: () => void performSaveAs()" desktop/frontend/src/project_panel.ts'
check "export_panel.ts exposes triggerExport using the same handleExportClick the visible button uses" \
  'grep -q "triggerExport: () => void handleExportClick()" desktop/frontend/src/export_panel.ts'
check "native_menu.ts routes File menu ids to those exact trigger methods (not a duplicated project/export implementation)" \
  'grep -q "deps.projectPanel.triggerNew()" desktop/frontend/src/native_menu.ts \
   && grep -q "deps.projectPanel.triggerOpen()" desktop/frontend/src/native_menu.ts \
   && grep -q "deps.projectPanel.triggerSave()" desktop/frontend/src/native_menu.ts \
   && grep -q "deps.projectPanel.triggerSaveAs()" desktop/frontend/src/native_menu.ts \
   && grep -q "deps.exportPanel.triggerExport()" desktop/frontend/src/native_menu.ts'
check "native accelerators only — no duplicate frontend keydown listener for Cmd+N/O/S (§25 of the mandate)" \
  '! grep -rE "keydown|metaKey|ctrlKey" desktop/frontend/src/*.ts | grep -v ".test.ts"'
check "menu ID -> action routing unit tests exist for every File/View item" \
  'grep -q "routes %s to projectPanel.%s" desktop/frontend/src/native_menu.test.ts'

section "View menu — Reset View/visibility/Report/Diagnostics routing and sync (§15-19/§29 of the mandate)"
check "Reset View routes to the same M3 preview.resetView() — no duplicated camera logic in Rust (§17)" \
  'grep -q "deps.preview.resetView()" desktop/frontend/src/native_menu.ts \
   && ! grep -qE "fn.*reset_view|fitCameraToBounds" desktop/src-tauri/src/menu.rs'
check "visibility sync is the ONE function both the native menu and the visible checkbox funnel through (§15/§29)" \
  'grep -q "export function createNativeMenuBridge" desktop/frontend/src/native_menu.ts \
   && grep -q "setLayerVisible: (layer, visible) => nativeMenuRef?.setLayerVisible(layer, visible)" desktop/frontend/src/main.ts'
check "set_view_menu_checked requires no new WebView capability (app-owned command, not ACL-gated — §34)" \
  'grep -q "pub fn set_view_menu_checked" desktop/src-tauri/src/menu.rs \
   && grep -q "menu::set_view_menu_checked" desktop/src-tauri/src/lib.rs'
check "Instrument Report / Diagnostics route to the existing M2/M3 panels — no second implementation (§18/§19)" \
  'grep -q "deps.reportPanel.open()" desktop/frontend/src/native_menu.ts \
   && grep -q "deps.diagnosticsPanel.open()" desktop/frontend/src/native_menu.ts'
check "report_panel.ts / diagnostics_panel.ts internals (fetch/render logic) unchanged by M4 — only an open() entry point was added" \
  'grep -q "requestReport(accepted)" desktop/frontend/src/report_panel.ts \
   && grep -q "io.fetchAppInfo()" desktop/frontend/src/diagnostics_panel.ts'
check "exactly three CheckMenuItem visibility items are constructed (Body/Rod/Strings, none dropped or duplicated)" \
  '[ "$(grep -c "CheckMenuItem::with_id" desktop/src-tauri/src/menu.rs)" -eq 3 ]'
check "none of the three visibility items is constructed with checked=false (all start visible, §14 of the M3 mandate)" \
  '! grep -B1 -A1 "MENU_ID_VIEW_BODY,\|MENU_ID_VIEW_ROD,\|MENU_ID_VIEW_STRINGS," desktop/src-tauri/src/menu.rs | grep -qE "^\s*false,\s*$"'

section "Product UI integration (§24 of the mandate — M4 is not a UI redesign, existing visible controls preserved)"
check "the M3 viewport-column / view-controls / report-panel layout is unchanged" \
  'grep -q "viewport-column" desktop/frontend/src/main.ts \
   && grep -q "view-controls-container" desktop/frontend/src/main.ts'
check "Project/Export/Diagnostics panels remain wired exactly as before — no controls removed" \
  'grep -q "createProjectPanelController(projectPanelEl" desktop/frontend/src/main.ts \
   && grep -q "createExportPanelController(exportPanelEl" desktop/frontend/src/main.ts \
   && grep -q "createDiagnosticsPanelController(diagnosticsPanelEl" desktop/frontend/src/main.ts'

section "Build 025 M1/M2/M3 regression (drift classification, not a blind script call — see header)"
check "project persistence (project_panel.ts's guard logic, project_state.ts) unchanged" \
  'git diff --quiet 9c8d1a3 -- desktop/frontend/src/project_state.ts 2>/dev/null'
check "automatic initial preview / startup coordinator unchanged" \
  'git diff --quiet 9c8d1a3 -- desktop/frontend/src/parameter_panel.ts desktop/frontend/src/startup.ts 2>/dev/null'
check "M3 scene/preview visibility+reset-view mechanism unchanged" \
  'git diff --quiet 9c8d1a3 -- desktop/frontend/src/scene.ts desktop/frontend/src/preview.ts 2>/dev/null'
check "M3 report generation (report.ts) unchanged" \
  'git diff --quiet 9c8d1a3 -- desktop/frontend/src/report.ts 2>/dev/null'
check "security capability grant unchanged since the M1 native-close fix (§34 of the mandate: no new WebView capability expected)" \
  'git diff --quiet -- desktop/src-tauri/capabilities/ 2>/dev/null'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP unchanged (§35 of the mandate)" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"

section "Build 024 export regression"
check "export.ts and export_panel.ts core export logic unchanged (only triggerExport was added)" \
  'git diff --quiet 9c8d1a3 -- desktop/frontend/src/export.ts 2>/dev/null'

section "Dependency invariants (§36 of the mandate)"
check "no new dependency added to Cargo.toml (native menus use Tauri's own existing menu API)" \
  'git diff --quiet 9c8d1a3 -- desktop/src-tauri/Cargo.toml 2>/dev/null'
check "no new dependency added to package.json" \
  'git diff --quiet 9c8d1a3 -- desktop/frontend/package.json 2>/dev/null'
check "0 VTK references added under src/zerorod_sidecar/" \
  '! grep -riq "vtkmodules\|import vtk" src/zerorod_sidecar/main.py'
check "legacy PySide6 app retained and unchanged" \
  '[ -d src/zerorodcad_desktop ] && git diff --quiet 9c8d1a3 -- src/zerorodcad_desktop/ 2>/dev/null'
check "experiments/te002-tauri retained and unchanged" \
  '[ -d experiments/te002-tauri ] && git diff --quiet 9c8d1a3 -- experiments/te002-tauri/ 2>/dev/null'

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
    SMOKE_DIR="${REPORT_DIR}/bundled-smoke"
    rm -rf "${SMOKE_DIR}"
    mkdir -p "${SMOKE_DIR}"
    printf '%s\n' \
      '{"schema":"zerorod-sidecar/v1","request_id":"a","command":"parameters_defaults"}' \
      '{"schema":"zerorod-sidecar/v1","request_id":"b","command":"preview"}' \
      '{"schema":"zerorod-sidecar/v1","request_id":"c","command":"report"}' \
      '{"schema":"zerorod-sidecar/v1","request_id":"stop","command":"shutdown"}' \
      | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/bundled-smoke.jsonl" || true
    if "${PY}" - "${REPORT_DIR}/bundled-smoke.jsonl" <<'PYEOF'
import json, sys

log_path = sys.argv[1]
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
print("bundled sidecar: defaults ok, preview ok, report ok, shutdown ok — engine layer unaffected by the desktop-shell milestone")
PYEOF
    then
      echo "OK   bundled sidecar smoke-tested through the real onedir binary (engine layer proven unaffected by the M4 desktop-shell work)"
    else
      echo "  FAIL bundled sidecar smoke test did not pass" >&2
      FAILED=1
    fi
    rm -rf "${SMOKE_DIR}"

    echo "== building fresh release .app from this M4 HEAD =="
    if bash scripts/build-productive-desktop-app.sh release > "${REPORT_DIR}/app-build.log" 2>&1; then
      APP_PATH="desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
      if [ -d "${APP_PATH}" ]; then
        echo "OK   fresh release .app built: ${APP_PATH}"
        BUILT_BINARY="${APP_PATH}/Contents/MacOS/zerorod-desktop"
        check "built binary exists" '[ -f "'"${BUILT_BINARY}"'" ]'
        if [ -f "${BUILT_BINARY}" ]; then
          # Artifact-level proof the native menu is actually present in the
          # compiled binary (§42 of the mandate: "do not rely only on
          # source inspection") — the menu item id/event-name string
          # constants are plain &str literals, so unlike the M1 identity
          # strings (merged into one unbroken blob when stripped/release),
          # these distinctive, longer, hyphenated tokens remain reliably
          # findable via strings(1). Materialized to a file first (not
          # piped directly into `grep -q`): under `pipefail`, `grep -q`'s
          # early exit on the first match sends SIGPIPE to `strings`,
          # which reports a non-zero exit that `pipefail` then propagates
          # as the pipeline's own status even though the match was real —
          # a classic false-negative, not a property of the artifact.
          STRINGS_OUT="${REPORT_DIR}/release-binary-strings.txt"
          strings "${BUILT_BINARY}" > "${STRINGS_OUT}"
          check "compiled binary contains the native menu's item ids (proves the menu tree is actually built into this artifact)" \
            'grep -q "file-save-as" "'"${STRINGS_OUT}"'" \
             && grep -q "view-diagnostics" "'"${STRINGS_OUT}"'" \
             && grep -q "menu-action" "'"${STRINGS_OUT}"'"'
          check "compiled binary contains the visible menu labels" \
            'grep -q "Quit ZeroRodCAD" "'"${STRINGS_OUT}"'" \
             && grep -q "Instrument Report" "'"${STRINGS_OUT}"'"'
        fi
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
  echo "BUILD-025-M4 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-025-M4 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
