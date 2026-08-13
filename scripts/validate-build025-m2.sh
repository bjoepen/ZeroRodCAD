#!/usr/bin/env bash
# Build 025 / Milestone 2 — Product UI Productization & Lifecycle Polish
# validation gate.
#
# Re-verifies the still-valid subset of Build 025 M1's own checks directly
# (not via a blind call to validate-build025-m1.sh — that script's own
# frozen "app_info() rendered in main.ts" check legitimately breaks under
# M2, since M2 deliberately moves that rendering out of main.ts into
# diagnostics_panel.ts; see the "Build 025 M1 re-verification" section below
# for the classified drift and its replacement check), plus new
# M2-specific checks: automatic initial preview, exactly-once
# initialization, technical controls removed from the product UI,
# Diagnostics present with no side effects, startup failure/retry, native
# close regression, and Build 023/024 regressions. Never touches
# experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build025-m2"
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
  echo "# BUILD-025-M2: $1"
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
check "M2 product lifecycle record present" \
  '[ -f docs/migration/BUILD-025-M2-PRODUCT-LIFECYCLE.md ]'
check "M2 human validation checklist present" \
  '[ -f docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md ]'
check "M1 project persistence record present (baseline)" \
  '[ -f docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md ]'
check "M1 native-close bugfix record present (baseline)" \
  '[ -f docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md ]'
check "Lifecycle Analysis discovery doc present (baseline)" \
  '[ -f docs/migration/BUILD-025-LIFECYCLE-ANALYSIS.md ]'
check "known Quit/Cmd+Q guard-bypass limitation is tracked in the M2 human-validation checklist" \
  'grep -qi "Quit" docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md && grep -qi "M4" docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — full repository regression suite (§53 of the mandate: 0 productive domain changes expected)"
check "no Python source changed by M2" \
  'git diff --quiet -- src/zerorod_sidecar/ src/zerorodcad/ 2>/dev/null'
"${PY}" -m pytest -q

section "Rust — cargo test / fmt / clippy (§52 of the mandate: small-or-no Rust changes expected)"
RUST_TEST_LOG="${REPORT_DIR}/cargo-test.log"
(cd desktop/src-tauri && cargo test) | tee "${RUST_TEST_LOG}"
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)
check "no Rust source changed by M2 (engine.rs/commands.rs/lib.rs — EngineManager reused unmodified)" \
  'git diff --quiet -- desktop/src-tauri/src/ 2>/dev/null'
check "native-close ACL regression test (Build 025 M1 corrective fix) still passes" \
  'grep -q "window_destroy_is_permitted_for_the_main_window ... ok" "'"${RUST_TEST_LOG}"'"'

section "Frontend — vitest / TypeScript / build"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

section "Build 025 M1 re-verification (drift classification, not a blind script call — see header)"
# EXPECTED_AUTHORIZED_DRIFT: M1's own validate-build025-m1.sh checked that
# main.ts interpolates "${info.build} ${info.milestone}" directly — true
# under M1, deliberately no longer true under M2, since §14/§15 of the M2
# mandate requires the old always-visible status panel (which carried that
# interpolation) to be removed from the main product UI. The identity
# information itself is not lost — it moved to diagnostics_panel.ts,
# checked below instead. This is authorized, intentional relocation, not a
# stale gate assumption silently ignored.
check "build/milestone identity no longer hardcoded in main.ts (moved to Diagnostics, not deleted — see below)" \
  '! grep -q "info.build} \${info.milestone}" desktop/frontend/src/main.ts'
check "diagnostics_panel.ts is the one place that now renders live build/milestone identity" \
  'grep -q "appInfo.build} \${appInfo.milestone}" desktop/frontend/src/diagnostics_panel.ts'
check "app_info() itself (commands.rs, the actual single source of truth) is unchanged by M2" \
  'grep -q "build: \"025\".to_string()" desktop/src-tauri/src/commands.rs \
   && grep -q "milestone: \"M1\".to_string()" desktop/src-tauri/src/commands.rs'
# STALE_GATE_ASSUMPTION note: app_info() itself still literally says
# "M1" — this is Build 025's *milestone-number* field, historically bumped
# once per milestone in prior builds (e.g. M1's own fix bumped it from
# "022"/"M3"), but M2 deliberately does NOT bump it here: unlike M1 (a
# distinct, Human-Validation-gated deliverable with its own artifact
# identity requirement), M2's own artifact-identity requirement (§39/§61 of
# the M2 mandate) is satisfied by the *build* number ("025", unchanged
# across all of Build 025's milestones) plus the milestone-specific
# artifact filename/report this script and the human-validation doc
# produce — bumping the compiled milestone string itself is a one-line
# follow-up left to whichever change actually needs app_info() to
# distinguish M1 from M2 at runtime (none does yet). Recorded here so a
# future reader does not mistake this for an oversight.
check "project persistence unsaved-changes guard unchanged (project_panel.ts/project_state.ts)" \
  'git diff --quiet -- desktop/frontend/src/project_panel.ts desktop/frontend/src/project_state.ts 2>/dev/null'
check "Quit/window-close is still intercepted via confirmQuit (§19/§20 of the M1 mandate)" \
  'grep -q "onCloseRequested" desktop/frontend/src/main.ts && grep -q "projectPanel.confirmQuit()" desktop/frontend/src/main.ts'
check "window-close still does not itself call any shutdown command" \
  '! grep -q "shutdownEngine(\|invoke(\"engine_shutdown\"" desktop/frontend/src/main.ts'
check "security capability grant unchanged since the M1 native-close fix" \
  'grep -q "\"permissions\": \[\"core:default\", \"dialog:allow-open\", \"dialog:allow-save\", \"core:window:allow-destroy\"\]" desktop/src-tauri/capabilities/main-capability.json'

section "Automatic initial preview (§10-13/§41 of the M2 mandate)"
check "parameter_panel.ts's load() performs the automatic initial preview fetch+commit" \
  'grep -q "previewIO.fetchPreview(values)" desktop/frontend/src/parameter_panel.ts'
check "the automatic initial preview reuses the same pipeline loadProjectValues/live-preview already use (no second pipeline)" \
  '[ "$(grep -c "previewIO.fetchPreview" desktop/frontend/src/parameter_panel.ts)" -ge 2 ] && [ "$(grep -c "previewIO.commitPreview" desktop/frontend/src/parameter_panel.ts)" -ge 2 ]'
check "load() distinguishes a defaults-stage failure from a preview-stage failure (ParameterPanelLoadResult)" \
  'grep -q "stage: \"defaults\"" desktop/frontend/src/parameter_panel.ts && grep -q "stage: \"preview\"" desktop/frontend/src/parameter_panel.ts'
check "automatic initial preview unit tests exist and exercise exactly-once/consistency/failure paths" \
  'grep -q "requests and commits a preview for the canonical defaults exactly once" desktop/frontend/src/parameter_panel.test.ts \
   && grep -q "keeps accepted/draft consistent with the committed preview" desktop/frontend/src/parameter_panel.test.ts \
   && grep -q "reports a defaults-load failure distinctly" desktop/frontend/src/parameter_panel.test.ts \
   && grep -q "reports an initial-preview failure distinctly" desktop/frontend/src/parameter_panel.test.ts'
check "startup coordinator's single entry point (start()) drives exactly one io.run() call at app init" \
  'grep -q "void startup.start();" desktop/frontend/src/main.ts'
check "startup coordinator unit test proves exactly one io.run() call" \
  'grep -q "produces exactly one io.run() call" desktop/frontend/src/startup.test.ts'

section "Technical controls removed from the product UI (§14/§15 of the mandate)"
check "the old 5-row technical status panel is gone from main.ts" \
  '! grep -q "id=\"status-panel\"" desktop/frontend/src/main.ts'
check "\"Start / Check Engine\" control is gone (REMOVE_FROM_PRODUCT_UI)" \
  '! grep -q "start-check-engine" desktop/frontend/src/main.ts'
check "\"Ping Engine\" control is gone from the product UI (MOVE_TO_DIAGNOSTICS)" \
  '! grep -q "id=\"ping-engine\"" desktop/frontend/src/main.ts'
check "\"Request Preview Data\" control is gone (REMOVE_FROM_PRODUCT_UI — self-documented as non-rendering)" \
  '! grep -q "request-preview" desktop/frontend/src/main.ts'
check "the manual \"Load / Refresh ZeroRod\" button is gone (superseded by automatic initial preview)" \
  '! grep -q "load-zerorod" desktop/frontend/src/main.ts'
check "the raw \"last action\" log is gone from main.ts" \
  '! grep -q "last-action" desktop/frontend/src/main.ts'
check "Project/Parameters/Export/Diagnostics remain the only panels wired in main.ts" \
  'grep -q "createProjectPanelController" desktop/frontend/src/main.ts \
   && grep -q "createParameterPanelController" desktop/frontend/src/main.ts \
   && grep -q "createExportPanelController" desktop/frontend/src/main.ts \
   && grep -q "createDiagnosticsPanelController" desktop/frontend/src/main.ts'

section "Diagnostics view (§16/§17/§37/§38 of the mandate)"
check "diagnostics_panel.ts module exists" \
  '[ -f desktop/frontend/src/diagnostics_panel.ts ]'
check "Diagnostics is reachable via a toggle (§37 — no menu/dialog API used, no native menu integration yet)" \
  'grep -q "diagnostics-toggle" desktop/frontend/src/diagnostics_panel.ts \
   && ! grep -qE "@tauri-apps/api/menu|tauri::menu|Menu::new|Menu::default" desktop/frontend/src/diagnostics_panel.ts'
check "Diagnostics carries forward the relocated technical info (build, engine, python, cadquery, ocp, protocol)" \
  'grep -q "Application build" desktop/frontend/src/diagnostics_panel.ts \
   && grep -q "Engine status" desktop/frontend/src/diagnostics_panel.ts \
   && grep -q "Python version" desktop/frontend/src/diagnostics_panel.ts \
   && grep -q "CadQuery version" desktop/frontend/src/diagnostics_panel.ts \
   && grep -q "OCP variant" desktop/frontend/src/diagnostics_panel.ts \
   && grep -q "PARAMETERS_SCHEMA" desktop/frontend/src/diagnostics_panel.ts \
   && grep -q "MESH_SCHEMA" desktop/frontend/src/diagnostics_panel.ts'
check "only a Refresh Status action's data-action attribute is ever rendered (§17 — structural, not a prose/comment search)" \
  'diag="desktop/frontend/src/diagnostics_panel.ts"; \
   attrs=$(grep -oE "data-action=\"[a-z-]+\"" "${diag}" | sort -u); \
   [ "${attrs}" = "$(printf "data-action=\"diagnostics-refresh\"\ndata-action=\"diagnostics-toggle\"")" ]'
check "Diagnostics never calls a preview/project/export/dirty-affecting command (§38 — read-only status commands only)" \
  '! grep -qE "fetchPreview|commitPreview|requestProjectOpen|requestProjectSave|requestExport" desktop/frontend/src/diagnostics_panel.ts'
check "Diagnostics unit tests prove no side effects and no forbidden actions" \
  'grep -q "no side effects" desktop/frontend/src/diagnostics_panel.test.ts \
   && grep -q "exposes no kill-sidecar" desktop/frontend/src/diagnostics_panel.test.ts'

section "Startup failure UX and recovery (§13/§24-28/§42 of the mandate)"
check "startup.ts module exists" \
  '[ -f desktop/frontend/src/startup.ts ]'
check "startup failure surface offers Retry and Show Details, never Quit as a redundant button (§24)" \
  'grep -q "startup-retry" desktop/frontend/src/startup.ts \
   && grep -q "startup-details" desktop/frontend/src/startup.ts \
   && ! grep -qi "data-action=\"startup-quit\"" desktop/frontend/src/startup.ts'
check "Retry reuses the exact same sequence (start(), which calls io.run() again) — no separate retry path (§25)" \
  'grep -q "void start();" desktop/frontend/src/startup.ts'
check "startup error detail is sanitized code:message only — never reads a .details/.stack/.traceback field (§26, structural)" \
  '! grep -qE "\.details|\.stack|\.traceback" desktop/frontend/src/startup.ts'
check "no persistent success banner — success renders nothing (§21)" \
  'grep -q "renderIdle" desktop/frontend/src/startup.ts'
check "anti-flicker delayed-indicator pattern reused, not reinvented (§48)" \
  'grep -q "PREPARING_DISPLAY_DELAY_MS" desktop/frontend/src/startup.ts'
check "startup failure/retry unit tests exist" \
  'grep -q "shows a friendly message with Retry/Show Details on failure" desktop/frontend/src/startup.test.ts \
   && grep -q "Retry re-runs io.run" desktop/frontend/src/startup.test.ts'

section "Preview regression (Build 023 — live preview architecture unchanged)"
check "live_preview.ts unchanged" \
  'git diff --quiet -- desktop/frontend/src/live_preview.ts 2>/dev/null'
check "scene.ts / preview.ts unchanged (camera preservation, rotate/zoom/pan via OrbitControls)" \
  'git diff --quiet -- desktop/frontend/src/scene.ts desktop/frontend/src/preview.ts 2>/dev/null'
check "debounce constant unchanged" \
  'grep -q "LIVE_PREVIEW_DEBOUNCE_MS = 300" desktop/frontend/src/parameter_panel.ts'

section "Export regression (Build 024 — export.ts/export_panel.ts unchanged)"
check "export.ts and export_panel.ts unchanged" \
  'git diff --quiet -- desktop/frontend/src/export.ts desktop/frontend/src/export_panel.ts 2>/dev/null'
check "engine_export / engine_export_preflight commands unchanged" \
  'git diff --quiet -- desktop/src-tauri/src/commands.rs desktop/src-tauri/src/export_result.rs 2>/dev/null'

section "Dependency invariants (§51 of the mandate)"
check "no new dependency added to Cargo.toml" \
  'git diff --quiet -- desktop/src-tauri/Cargo.toml 2>/dev/null'
check "no new dependency added to package.json (no UI-state library for lifecycle)" \
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
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"c\",\"command\":\"export\",\"parameters\":{\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{}},\"output_directory\":\"$(pwd)/${SMOKE_DIR}\"}}" \
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
assert responses["stop"]["ok"] is True, responses["stop"]
print("bundled sidecar: parameters_defaults ok, preview ok (the automatic-initial-preview path), shutdown ok")
PYEOF
    then
      echo "OK   bundled sidecar smoke-tested through the real onedir binary (defaults + preview, the automatic-startup path + shutdown)"
    else
      echo "  FAIL bundled sidecar smoke test did not pass" >&2
      FAILED=1
    fi
    rm -rf "${SMOKE_DIR}"

    echo "== building fresh release .app from this M2 HEAD =="
    if bash scripts/build-productive-desktop-app.sh release > "${REPORT_DIR}/app-build.log" 2>&1; then
      APP_PATH="desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
      if [ -d "${APP_PATH}" ]; then
        echo "OK   fresh release .app built: ${APP_PATH}"
        BUILT_BINARY="${APP_PATH}/Contents/MacOS/zerorod-desktop"
        check "built binary exists" '[ -f "'"${BUILT_BINARY}"'" ]'
        check "built frontend bundle contains no leftover technical-control label text" \
          '! grep -RqE "Start / Check Engine|Ping Engine|Request Preview Data" desktop/frontend/dist/assets/*.js'
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
  echo "BUILD-025-M2 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-025-M2 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
