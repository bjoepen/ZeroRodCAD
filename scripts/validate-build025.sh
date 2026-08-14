#!/usr/bin/env bash
# Build 025 — MASTER validation gate (Milestone 5 / Integration, Completion &
# Repository Cleanup).
#
# This is the authoritative Build 025 completion gate. Like
# scripts/validate-build024.sh before it, it re-verifies the *current,
# integrated* state of Build 025 directly rather than chain-calling the
# per-milestone scripts (validate-build025-m1.sh..-m4.sh), which each encode a
# frozen "unchanged since this milestone's own baseline" invariant that later,
# legitimately-authorized milestones break by design.
#
# Never touches experiments/, tools/poc/, or the legacy PySide6 app beyond
# read-only diffing against a known-good baseline commit.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build025-master"
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
  echo "# BUILD-025 MASTER: $1"
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
require_nonzero_tests() {
  # Guards against a filtered/empty test selection silently "passing".
  local label="$1"
  local count="$2"
  if [ -z "${count}" ] || [ "${count}" -eq 0 ]; then
    echo "  FAIL ${label}: 0 tests executed — a filtered/empty run is not a pass" >&2
    FAILED=1
  else
    echo "  OK   ${label}: ${count} tests executed"
  fi
}

section "Documentation present — Build 025 complete milestone set"
check "M1 project persistence record present"    '[ -f docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md ]'
check "M1 native-close bugfix record present"     '[ -f docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md ]'
check "M1 human validation record present"        '[ -f docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md ]'
check "M2 product lifecycle record present"       '[ -f docs/migration/BUILD-025-M2-PRODUCT-LIFECYCLE.md ]'
check "M2 human validation record present"        '[ -f docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md ]'
check "M3 preview/report parity record present"   '[ -f docs/migration/BUILD-025-M3-PREVIEW-REPORT-PARITY.md ]'
check "M3 human validation record present"        '[ -f docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md ]'
check "M4 desktop shell record present"           '[ -f docs/migration/BUILD-025-M4-DESKTOP-SHELL.md ]'
check "M4 human validation record present"        '[ -f docs/migration/BUILD-025-M4-HUMAN-VALIDATION.md ]'
check "M5 repository cleanup record present"      '[ -f docs/migration/BUILD-025-M5-REPOSITORY-CLEANUP.md ]'
check "Build 025 completion record present"       '[ -f docs/migration/BUILD-025-COMPLETION.md ]'

section "Human validation history — all rounds PASS"
check "M1 human validation reads PASS"  'grep -q "Result | \*\*PASS\*\*" docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md'
check "M2 human validation reads PASS"  'grep -q "Result | \*\*PASS\*\*" docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md'
check "M3 human validation reads PASS"  'grep -q "Result | \*\*PASS\*\*" docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md'
check "M4 human validation reads PASS"  'grep -q "\*\*PASS\*\*" docs/migration/BUILD-025-M4-HUMAN-VALIDATION.md'

section "Contract invariants — no protocol v2, no undocumented version bump"
check "zerorod-parameters/v1 contract doc present, unchanged identifier" \
  'grep -q "zerorod-parameters/v1" docs/contracts/ZEROROD-PARAMETERS-V1.md'
check "sidecar protocol module still declares zerorod-sidecar/v1" \
  'grep -q "SIDECAR_SCHEMA = \"zerorod-sidecar/v1\"" src/zerorod_sidecar/protocol.py'
check "Rust protocol module still targets zerorod-sidecar/v1" \
  'grep -q "zerorod-sidecar/v1" desktop/src-tauri/src/protocol.rs'
check "mesh contract still zerorod-mesh/v1 (Python)" \
  'grep -rq "zerorod-mesh/v1" src/zerorod_sidecar/'
check "mesh contract still zerorod-mesh/v1 (Rust)" \
  'grep -q "zerorod-mesh/v1" desktop/src-tauri/src/mesh.rs'
check "legacy .zerorod project format reused unmodified (project.py present)" \
  '[ -f src/zerorodcad/project.py ]'
check "sidecar project_open/project_save commands registered" \
  'grep -q "\"project_open\"" src/zerorod_sidecar/main.py && grep -q "\"project_save\"" src/zerorod_sidecar/main.py'
check "sidecar report command registered, reuses build_report (no duplicated formula)" \
  'grep -q "\"report\"" src/zerorod_sidecar/main.py && grep -q "build_report" src/zerorod_sidecar/main.py'
check "all Build 025 Rust commands registered in the Tauri invoke handler" \
  'grep -q "commands::engine_project_open" desktop/src-tauri/src/lib.rs \
   && grep -q "commands::engine_project_save" desktop/src-tauri/src/lib.rs \
   && grep -q "commands::engine_report" desktop/src-tauri/src/lib.rs \
   && grep -q "menu::set_view_menu_checked" desktop/src-tauri/src/lib.rs'
check "export_result structural validation (Build 024 M3) still guards engine_export" \
  'grep -q "validate_export_result(&payload)" desktop/src-tauri/src/commands.rs'

section "Architecture conformance — ADR-022-001 (current, integrated state)"
check "Tauri v2 CLI/API pinned" \
  'grep -q "\"@tauri-apps/cli\": \"\^2\." desktop/frontend/package.json && grep -q "\"@tauri-apps/api\": \"\^2\." desktop/frontend/package.json'
check "Three.js present" \
  'grep -q "\"three\":" desktop/frontend/package.json'
check "Rust owns the persistent sidecar (engine.rs present)" \
  '[ -f desktop/src-tauri/src/engine.rs ]'
check "WebView never imports the shell plugin directly in frontend source" \
  '! grep -rq "@tauri-apps/plugin-shell" desktop/frontend/src/'
check "WebView capability is exactly the four Build-025 authorized permissions (no drift)" \
  'grep -q "\"permissions\": \[\"core:default\", \"dialog:allow-open\", \"dialog:allow-save\", \"core:window:allow-destroy\"\]" desktop/src-tauri/capabilities/main-capability.json'
check "no fs:* permission granted to the WebView" \
  '! grep -q "\"fs:" desktop/src-tauri/capabilities/main-capability.json'
check "no shell:*/process:* capability exposed to the WebView" \
  '! grep -q "shell:allow\|process:allow" desktop/src-tauri/capabilities/main-capability.json'
check "no message/ask/confirm dialog capability granted" \
  '! grep -qE "dialog:(allow-message|allow-ask|allow-confirm)" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP unchanged" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'
check "onedir-only sidecar packaging spec (COLLECT present)" \
  'grep -q "COLLECT" packaging/tauri/sidecar-onedir.spec'
check "numba/llvmlite/scipy excluded from the packaging spec" \
  'grep -q "numba" packaging/tauri/sidecar-onedir.spec && grep -q "llvmlite" packaging/tauri/sidecar-onedir.spec && grep -q "scipy" packaging/tauri/sidecar-onedir.spec'
check "hash-gated dylib dedup script present" \
  '[ -f packaging/tauri/dedup_bundle_dylibs.py ]'
check "reproducible build pipeline script present" \
  '[ -x scripts/build-productive-desktop-app.sh ]'
check "request timeout unchanged (30s)" \
  'grep -q "REQUEST_TIMEOUT_SECS: u64 = 30" desktop/src-tauri/src/engine.rs'
check "native Quit never uses PredefinedMenuItem::quit (M1 guard-bypass gap stays fixed)" \
  '! grep -vE "^\s*//" desktop/src-tauri/src/menu.rs | grep -q "PredefinedMenuItem::quit("'
check "legacy PySide6 app retained and untouched by Build 025" \
  '[ -d src/zerorodcad_desktop ] && git diff --quiet 7af13cc -- src/zerorodcad_desktop/ 2>/dev/null'
check "experiments/ retained and untouched by Build 025" \
  '[ -d experiments ] && git diff --quiet 7af13cc -- experiments/ 2>/dev/null'
check "tools/poc/ retained and untouched by Build 025" \
  '[ -d tools/poc ] && git diff --quiet 7af13cc -- tools/poc/ 2>/dev/null'
check "0 VTK references in the export/sidecar source" \
  '! grep -riq "vtkmodules\|import vtk" src/zerorod_sidecar/main.py src/zerorodcad/export.py'

section "Repository cleanup integrity — no accidentally tracked generated artifacts"
check "no target/node_modules/dist/build directories tracked by git" \
  '[ -z "$(git ls-files | grep -E "(^|/)(target|node_modules|dist|build)/" || true)" ]'
check "no .DS_Store / __pycache__ / .pyc tracked by git" \
  '[ -z "$(git ls-files | grep -E "\.DS_Store$|__pycache__|\.pyc$" || true)" ]'

section "Full test suites — Python (Ruff + pytest, no filtered zero-test selection)"
"${PY}" -m ruff check src/ tests/
"${PY}" -m ruff format --check src/ tests/
echo "ruff clean"
PY_LOG="${REPORT_DIR}/pytest.log"
"${PY}" -m pytest -q | tee "${PY_LOG}"
PY_COUNT=$(grep -oE "[0-9]+ passed" "${PY_LOG}" | tail -1 | grep -oE "[0-9]+" || echo "")
require_nonzero_tests "Python full suite" "${PY_COUNT}"

section "Full test suites — Rust (cargo test / fmt / clippy, no filtered zero-test selection)"
RUST_LOG="${REPORT_DIR}/cargo-test.log"
(cd desktop/src-tauri && cargo test) | tee "${RUST_LOG}"
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)
RUST_COUNT=$(grep -oE "^test result: ok\. [0-9]+ passed" "${RUST_LOG}" | grep -oE "[0-9]+" | awk '{s+=$1} END{print s+0}')
require_nonzero_tests "Rust suite (summed across all binaries)" "${RUST_COUNT}"
check "project persistence IPC argument-binding regression tests still green" \
  'grep -q "ipc_argument_binding" "'"${RUST_LOG}"'"'
check "native menu event-boundary regression tests still green" \
  'grep -q "routing_quit_to_window_close_does_not_panic_with_only_a_main_window_present ... ok" "'"${RUST_LOG}"'" \
   && grep -q "routing_a_non_quit_id_with_no_menu_present_does_not_panic ... ok" "'"${RUST_LOG}"'"'

section "Full test suites — Frontend (vitest / TypeScript / production build, no filtered zero-test selection)"
FRONT_LOG="${REPORT_DIR}/vitest.log"
(cd desktop/frontend && npm run test -- --run) | tee "${FRONT_LOG}"
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)
FRONT_COUNT=$(grep -oE "Tests +[0-9]+ passed" "${FRONT_LOG}" | tail -1 | grep -oE "[0-9]+" || echo "")
require_nonzero_tests "Frontend vitest suite" "${FRONT_COUNT}"

section "Dependency invariants — VTK / PySide6 / Qt / numba / llvmlite / scipy = 0 (meaningful detection, not filename-only)"
BUNDLE_VENV=".venv-novtk-bundle"
SIDECAR_DIST="desktop/sidecar-dist"
if [ -x "${BUNDLE_VENV}/bin/python" ]; then
  check "cadquery-ocp-novtk (not cadquery-ocp) in the packaging build environment" \
    "${BUNDLE_VENV}/bin/pip show cadquery-ocp-novtk >/dev/null 2>&1"
else
  echo "SKIPPED: ${BUNDLE_VENV} not found."
fi

section "Real end-to-end final pipeline — freshly rebuilt productive onedir sidecar"
if [ -x "${BUNDLE_VENV}/bin/python" ]; then
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

    echo "== Dependency invariants — meaningful detection against the fresh bundle =="
    for pat in "*vtk*" "*pyside*" "*[Qq]t*" "*numba*" "*llvmlite*" "*scipy*"; do
      matches=$(find "${SIDECAR_DIST}" -iname "${pat}" 2>/dev/null | grep -v "cadquery_ocp_novtk" || true)
      if [ -n "${matches}" ]; then
        echo "  FAIL unexpected match for '${pat}': ${matches}" >&2
        FAILED=1
      fi
    done
    echo "  OK   0 VTK/PySide6/Qt/numba/llvmlite/scipy files in the fresh sidecar dist"

    DEFAULT_DIR="${REPORT_DIR}/e2e-default"
    ALT_DIR="${REPORT_DIR}/e2e-alt"
    PROJECT_DIR="${REPORT_DIR}/e2e-project"
    rm -rf "${DEFAULT_DIR}" "${ALT_DIR}" "${PROJECT_DIR}"
    mkdir -p "${DEFAULT_DIR}" "${ALT_DIR}" "${PROJECT_DIR}"
    printf '%s\n' \
      '{"schema":"zerorod-sidecar/v1","request_id":"status","command":"status"}' \
      '{"schema":"zerorod-sidecar/v1","request_id":"preview-defaults","command":"preview"}' \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"preview-alt\",\"command\":\"preview\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":60.0}}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"report-alt\",\"command\":\"report\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":60.0}}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"project-save\",\"command\":\"project_save\",\"parameters\":{\"path\":\"$(pwd)/${PROJECT_DIR}/master-gate.zerorod\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":60.0}}}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"project-open\",\"command\":\"project_open\",\"parameters\":{\"path\":\"$(pwd)/${PROJECT_DIR}/master-gate.zerorod\"}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"export-alt\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${ALT_DIR}\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":60.0}}}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"preflight-conflict\",\"command\":\"export_preflight\",\"parameters\":{\"output_directory\":\"$(pwd)/${ALT_DIR}\"}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"export-invalid\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${ALT_DIR}\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":-1.0}}}}" \
      '{"schema":"zerorod-sidecar/v1","request_id":"preview-defaults-2","command":"preview"}' \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"export-defaults\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${DEFAULT_DIR}\"}}" \
      '{"schema":"zerorod-sidecar/v1","request_id":"stop","command":"shutdown"}' \
      | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/e2e-smoke.jsonl" || true

    if "${PY}" - "${REPORT_DIR}/e2e-smoke.jsonl" "${DEFAULT_DIR}" "${ALT_DIR}" "${PROJECT_DIR}" <<'PYEOF'
import json, sys
from pathlib import Path

log_path, default_dir, alt_dir, project_dir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
responses = {}
with open(log_path) as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            responses[r["request_id"]] = r

assert responses["status"]["ok"] is True, responses["status"]
assert responses["preview-defaults"]["ok"] is True
assert responses["preview-alt"]["ok"] is True
assert responses["report-alt"]["ok"] is True, responses["report-alt"]
assert responses["project-save"]["ok"] is True, responses["project-save"]
assert Path(project_dir / "master-gate.zerorod").is_file()
assert responses["project-open"]["ok"] is True, responses["project-open"]
opened_values = responses["project-open"]["result"]["values"]
assert opened_values["body_width"] == 60.0, opened_values
assert responses["export-alt"]["ok"] is True, responses["export-alt"]
assert responses["preflight-conflict"]["ok"] is True
assert responses["preflight-conflict"]["result"]["has_conflicts"] is True, responses["preflight-conflict"]
assert responses["export-invalid"]["ok"] is False, responses["export-invalid"]
assert responses["export-invalid"]["error"]["code"] in ("invalid_parameters_domain", "invalid_parameters"), responses["export-invalid"]
assert responses["preview-defaults-2"]["ok"] is True
assert responses["export-defaults"]["ok"] is True
assert responses["stop"]["ok"] is True

for rid, directory in (("export-alt", alt_dir), ("export-defaults", default_dir)):
    files = responses[rid]["result"]["files"]
    assert len(files) == 3, files
    roles = {f["role"] for f in files}
    assert roles == {"body_stl", "assembly_step", "report_markdown"}, roles
    for entry in files:
        p = Path(entry["path"])
        assert p.is_file() and p.stat().st_size > 0, entry

alt_files = {f["role"]: f["path"] for f in responses["export-alt"]["result"]["files"]}
default_files = {f["role"]: f["path"] for f in responses["export-defaults"]["result"]["files"]}
alt_report = Path(alt_files["report_markdown"]).read_text()
default_report = Path(default_files["report_markdown"]).read_text()
assert "60.00 mm" in alt_report, "alternate export report does not reflect body_width=60"
assert "60.00 mm" not in default_report, "default export report unexpectedly reflects body_width=60"
assert Path(alt_files["body_stl"]).read_bytes() != Path(default_files["body_stl"]).read_bytes()

live_report = responses["report-alt"]["result"].get("markdown")
assert live_report is not None, responses["report-alt"]
assert "60.00 mm" in live_report, "live report command does not match export's report.md content"

print("real end-to-end pipeline: status, preview x3, report, project save/open roundtrip, "
      "export x2 (alt/default), preflight-conflict, invalid-parameter recovery, "
      "all outputs valid, accepted-state semantics confirmed, shutdown ok")
PYEOF
    then
      echo "  OK   real end-to-end final pipeline passed (project roundtrip, report, preflight, false-success prevention, valid-after-error, output verification)"
    else
      echo "  FAIL real end-to-end final pipeline did not pass" >&2
      FAILED=1
    fi
    rm -rf "${DEFAULT_DIR}" "${ALT_DIR}" "${PROJECT_DIR}"
    rm -rf "${SIDECAR_DIST}" build/zerorod-engine
  else
    echo "  FAIL productive onedir sidecar rebuild failed. Log: ${REPORT_DIR}/pyinstaller-rebuild.log" >&2
    tail -10 "${REPORT_DIR}/pyinstaller-rebuild.log" || true
    FAILED=1
  fi
else
  echo "SKIPPED: ${BUNDLE_VENV} not found. Run scripts/validate-te0012-novtk-bundle.sh first."
fi

echo ""
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
  echo "BUILD-025 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-025 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
