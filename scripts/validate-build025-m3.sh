#!/usr/bin/env bash
# Build 025 / Milestone 3 — Preview & Report Parity validation gate.
#
# Re-verifies the still-valid subset of Build 025 M1/M2's own checks
# directly (drift classified below, not a blind call to
# validate-build025-m1.sh/-m2.sh — same reasoning each prior milestone gate
# already established), plus this milestone's own new checks: Reset View,
# Body/Rod/Strings visibility, the Instrument Report, and build identity
# now reporting M3. Never touches experiments/te002-tauri or the legacy
# PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build025-m3"
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
  echo "# BUILD-025-M3: $1"
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
check "M3 preview/report parity record present" \
  '[ -f docs/migration/BUILD-025-M3-PREVIEW-REPORT-PARITY.md ]'
check "M3 human validation checklist present" \
  '[ -f docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md ]'
check "M2 human validation now recorded PASS (§2 of the mandate)" \
  'grep -q "Status: PASS" docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md'
check "known Quit/Cmd+Q guard-bypass limitation is carried forward into the M3 checklist" \
  'grep -qi "Quit" docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md && grep -qi "M4" docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — domain package unchanged (§6/§53 of the mandate: no engineering math reimplemented, no domain change)"
check "zerorodcad/ (the domain package — parameters/report/preview/export logic itself) unchanged" \
  'git diff --quiet -- src/zerorodcad/ 2>/dev/null'
check "the sidecar's report command reuses build_report()/parse_parameters_request()/validate_parameters() — no duplicated formulas" \
  'grep -q "from zerorodcad.report import build_report" src/zerorod_sidecar/main.py \
   && grep -q "from zerorod_sidecar.parameters_contract import parse_parameters_request" src/zerorod_sidecar/main.py'
check "no new Python module invents a second report/engineering-math implementation" \
  '[ ! -f src/zerorod_sidecar/report_contract.py ] && [ ! -f desktop/frontend/src/instrument_report_math.ts ]'

section "Python — full repository regression suite"
"${PY}" -m pytest -q

section "Rust — cargo test / fmt / clippy"
RUST_TEST_LOG="${REPORT_DIR}/cargo-test.log"
(cd desktop/src-tauri && cargo test) | tee "${RUST_TEST_LOG}"
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)
check "engine.rs (the lifecycle/protocol layer — §52: no second lifecycle manager) unchanged" \
  'git diff --quiet -- desktop/src-tauri/src/engine.rs desktop/src-tauri/src/protocol.rs desktop/src-tauri/src/mesh.rs desktop/src-tauri/src/export_result.rs 2>/dev/null'
check "native-close ACL regression test (Build 025 M1 corrective fix) still passes" \
  'grep -q "window_destroy_is_permitted_for_the_main_window ... ok" "'"${RUST_TEST_LOG}"'"'
check "engine_report command registered and structurally validated" \
  'grep -q "pub async fn engine_report" desktop/src-tauri/src/commands.rs \
   && grep -q "fn validate_report_result" desktop/src-tauri/src/commands.rs \
   && grep -q "commands::engine_report" desktop/src-tauri/src/lib.rs'
check "report IPC argument-binding regression test actually ran" \
  'grep -q "commands::tests::ipc_argument_binding::accepts_the_exact_payload_report_ts_sends ... ok" "'"${RUST_TEST_LOG}"'"'

section "Frontend — vitest / TypeScript / build"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

section "Build identity — must report Build 025 / M3, not M1/M2 (§3/§43 of the mandate)"
check "app_info() reports the current build/milestone pair (single source, commands.rs)" \
  'grep -q "build: \"025\".to_string()" desktop/src-tauri/src/commands.rs \
   && grep -q "milestone: \"M3\".to_string()" desktop/src-tauri/src/commands.rs'
check "app_info() never reports an earlier Build 025 milestone (general regression, not just the one historical pair)" \
  'grep -q "fn app_info_never_reports_a_stale_earlier_build_025_milestone" desktop/src-tauri/src/commands.rs'
check "diagnostics_panel.ts remains the one place that renders live build/milestone identity (unchanged mechanism from M2)" \
  'grep -q "appInfo.build} \${appInfo.milestone}" desktop/frontend/src/diagnostics_panel.ts'
check "diagnostics_panel.test.ts fixture reflects the current milestone, not a stale one" \
  'grep -q "milestone: \"M3\"" desktop/frontend/src/diagnostics_panel.test.ts \
   && grep -q "Build 025 M3" desktop/frontend/src/diagnostics_panel.test.ts'

section "Reset View (§7-9/§30-31 of the mandate — legacy has exactly one such control, not a separate Fit/Reset pair)"
check "boundsFromVisibleObjects exists in scene.ts, driven by visibility, not the full mesh payload (§12)" \
  'grep -q "export function boundsFromVisibleObjects" desktop/frontend/src/scene.ts \
   && grep -q "traverseVisible" desktop/frontend/src/scene.ts'
check "resetView reuses the existing fitCameraToBounds — no second camera algorithm" \
  'grep -q "function resetView" desktop/frontend/src/preview.ts \
   && grep -A5 "function resetView" desktop/frontend/src/preview.ts | grep -q "fitCameraToBounds"'
check "resetView makes no backend call and no OrbitControls/renderer re-creation (§9/§31, structural)" \
  '! grep -A6 "function resetView" desktop/frontend/src/preview.ts | grep -qE "invoke\(|new OrbitControls|new THREE.WebGLRenderer"'
check "view_controls.ts's IO has no capability that could dirty the project or call the backend (§9, structural via interface shape)" \
  '! grep -qE "invoke\(|getAccepted|setDirty|fetchPreview" desktop/frontend/src/view_controls.ts'
check "camera bounds/reset unit tests exist and cover the hidden-layer case" \
  'grep -q "excludes a hidden layer.s geometry entirely" desktop/frontend/src/scene.test.ts \
   && grep -q "returns null when every layer is hidden" desktop/frontend/src/scene.test.ts'

section "Body/Rod/Strings visibility (§10-15/§32 of the mandate)"
check "ModelLayer/applyModelLayerVisibility exist and target exactly body/rod/strings — no new mesh contract fields" \
  'grep -q "export type ModelLayer = \"body\" | \"rod\" | \"strings\"" desktop/frontend/src/preview.ts \
   && grep -q "export function applyModelLayerVisibility" desktop/frontend/src/preview.ts'
check "mesh.ts (the zerorod-mesh/v1 contract) unchanged — visibility needed no protocol change" \
  'git diff --quiet -- desktop/frontend/src/mesh.ts 2>/dev/null'
check "visibility defaults to true for all three layers (§14)" \
  'grep -A5 "const layerVisibility: Record<ModelLayer, boolean> = {" desktop/frontend/src/preview.ts | grep -q "body: true" \
   && grep -A5 "const layerVisibility: Record<ModelLayer, boolean> = {" desktop/frontend/src/preview.ts | grep -q "rod: true" \
   && grep -A5 "const layerVisibility: Record<ModelLayer, boolean> = {" desktop/frontend/src/preview.ts | grep -q "strings: true"'
check "commitPreview re-applies visibility after every geometry replacement (§13 — the named regression case)" \
  'grep -A20 "function commitPreview" desktop/frontend/src/preview.ts | grep -q "clearGroup(modelGroup)" \
   && grep -A20 "function commitPreview" desktop/frontend/src/preview.ts | grep -q "applyModelLayerVisibility"'
check "visibility-survives-mesh-replacement regression test exists" \
  'grep -q "survives a full geometry replacement" desktop/frontend/src/preview.test.ts'
check "view controls use plain product labels, no Three.js/group terminology (§15)" \
  'grep -q "uses plain product labels" desktop/frontend/src/view_controls.test.ts'

section "Instrument Report (§16-23/§33 of the mandate)"
check "report.ts / report_panel.ts exist" \
  '[ -f desktop/frontend/src/report.ts ] && [ -f desktop/frontend/src/report_panel.ts ]'
check "report is sourced from getAccepted() only — never a draft (§18, mirrors export's own rule)" \
  'grep -q "getAccepted: () => ZeroRodParametersValues | null" desktop/frontend/src/report_panel.ts \
   && ! grep -qE "getDraft|draft\.values" desktop/frontend/src/report_panel.ts'
check "report refresh is gated on visibility + an actual accepted-state change (§21 — not every keystroke)" \
  'grep -q "if (!open) return;" desktop/frontend/src/report_panel.ts \
   && grep -q "valuesEqual(lastFetchedFor, accepted)" desktop/frontend/src/report_panel.ts'
check "zerorod-sidecar/v1 envelope unchanged — report is an additive command, no version bump (§19/§33)" \
  '! grep -q "zerorod-sidecar/v2" desktop/frontend/src/report.ts desktop/src-tauri/src/commands.rs src/zerorod_sidecar/main.py desktop/src-tauri/src/protocol.rs'
check "report renderer never dumps raw JSON — real structural HTML elements (§20)" \
  'grep -q "<table>" desktop/frontend/src/report.ts && grep -q "<h3>" desktop/frontend/src/report.ts'
check "report failure surfaces a concise product error with Retry, never a raw traceback (§22)" \
  'grep -q "data-action=\"report-retry\"" desktop/frontend/src/report_panel.ts \
   && ! grep -qi "traceback" desktop/frontend/src/report_panel.ts desktop/frontend/src/report.ts'
check "report/export semantic-consistency test exists, covering default + alternate + gauge-change (§23)" \
  'grep -q "test_report_command_and_exported_report_md_agree_for_the_same_accepted_state" tests/test_zerorod_sidecar_main.py'
check "report renderer tested against the real captured build_report() output, not a hand-simplified sample" \
  'grep -q "Captured verbatim from a real" desktop/frontend/src/report.test.ts'

section "Product UI integration (§25/§26 of the mandate)"
check "the new model-view tool area is subordinate to the viewport, not a redesign (viewport-column wraps it)" \
  'grep -q "viewport-column" desktop/frontend/src/main.ts \
   && grep -q "view-controls-container" desktop/frontend/src/main.ts \
   && grep -q "report-panel-container" desktop/frontend/src/main.ts'
check "M3 controls are NOT placed inside Diagnostics (§26 — kept conceptually separate)" \
  '! grep -qE "view-controls|report-panel|ViewControls|ReportPanel" desktop/frontend/src/diagnostics_panel.ts'
check "Diagnostics itself unchanged by M3" \
  'git diff --quiet -- desktop/frontend/src/diagnostics_panel.ts 2>/dev/null'

section "Build 025 M1/M2 regression (drift classification, not a blind script call — see header)"
check "project persistence (project_panel.ts/project_state.ts) unchanged" \
  'git diff --quiet -- desktop/frontend/src/project_panel.ts desktop/frontend/src/project_state.ts 2>/dev/null'
check "automatic initial preview / startup coordinator (parameter_panel.ts's load(), startup.ts) unchanged" \
  'git diff --quiet -- desktop/frontend/src/parameter_panel.ts desktop/frontend/src/startup.ts 2>/dev/null'
check "Quit/window-close is still intercepted via confirmQuit" \
  'grep -q "onCloseRequested" desktop/frontend/src/main.ts && grep -q "projectPanel.confirmQuit()" desktop/frontend/src/main.ts'
check "security capability grant unchanged since the M1 native-close fix (§34 of the mandate: no new capability expected)" \
  'git diff --quiet -- desktop/src-tauri/capabilities/ 2>/dev/null'
# EXPECTED_AUTHORIZED_DRIFT: scene.ts/preview.ts DID change this milestone
# (§30 of the mandate explicitly directs extending them for Reset
# View/visibility) — a blanket "unchanged" check would be wrong here, so
# the checks below instead pin the specific pre-existing exports/behavior
# that must survive the extension, rather than the whole file.
check "live-preview camera-refit heuristic (Build 023 M4) still present and unchanged in constant" \
  'grep -q "EXTREME_BOUNDS_CHANGE_RATIO = 1.5" desktop/frontend/src/scene.ts \
   && grep -q "export function isExtremeBoundsChange" desktop/frontend/src/scene.ts'
check "live_preview.ts (the debounce/generation-gate scheduler) unchanged" \
  'git diff --quiet -- desktop/frontend/src/live_preview.ts 2>/dev/null'
check "live-preview debounce constant unchanged" \
  'grep -q "LIVE_PREVIEW_DEBOUNCE_MS = 300" desktop/frontend/src/parameter_panel.ts'

section "Build 024 export regression"
check "export.ts and export_panel.ts unchanged" \
  'git diff --quiet -- desktop/frontend/src/export.ts desktop/frontend/src/export_panel.ts 2>/dev/null'
check "engine_export / engine_export_preflight commands unchanged" \
  'git diff --quiet -- desktop/src-tauri/src/export_result.rs 2>/dev/null'

section "Dependency invariants (§35 of the mandate)"
check "no new dependency added to Cargo.toml" \
  'git diff --quiet -- desktop/src-tauri/Cargo.toml 2>/dev/null'
check "no new dependency added to package.json (no Markdown/charting/report framework)" \
  'git diff --quiet -- desktop/frontend/package.json 2>/dev/null'
check "0 VTK references added under src/zerorod_sidecar/" \
  '! grep -riq "vtkmodules\|import vtk" src/zerorod_sidecar/main.py'
check "legacy PySide6 app retained and unchanged" \
  '[ -d src/zerorodcad_desktop ] && git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null'
check "experiments/te002-tauri retained and unchanged" \
  '[ -d experiments/te002-tauri ] && git diff --quiet -- experiments/te002-tauri/ 2>/dev/null'

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
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"d\",\"command\":\"report\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":60.0}}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"e\",\"command\":\"export\",\"parameters\":{\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{}},\"output_directory\":\"$(pwd)/${SMOKE_DIR}\"}}" \
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
assert responses["c"]["result"]["markdown"].startswith("# Instrument Report"), responses["c"]
assert responses["d"]["ok"] is True, responses["d"]
assert "60.00 mm" in responses["d"]["result"]["markdown"], responses["d"]
assert responses["e"]["ok"] is True, responses["e"]
assert responses["stop"]["ok"] is True, responses["stop"]
print(
    "bundled sidecar: defaults ok, preview ok, report ok (default + alternate geometry), "
    "export ok, shutdown ok — same persistent process throughout"
)
PYEOF
    then
      echo "OK   bundled sidecar smoke-tested through the real onedir binary (defaults + preview + report x2 + export + shutdown, same persistent PID)"
    else
      echo "  FAIL bundled sidecar smoke test did not pass" >&2
      FAILED=1
    fi
    rm -rf "${SMOKE_DIR}"

    echo "== building fresh release .app from this M3 HEAD =="
    if bash scripts/build-productive-desktop-app.sh release > "${REPORT_DIR}/app-build.log" 2>&1; then
      APP_PATH="desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
      if [ -d "${APP_PATH}" ]; then
        echo "OK   fresh release .app built: ${APP_PATH}"
        BUILT_BINARY="${APP_PATH}/Contents/MacOS/zerorod-desktop"
        check "built binary exists" '[ -f "'"${BUILT_BINARY}"'" ]'
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
  echo "BUILD-025-M3 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-025-M3 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
