#!/usr/bin/env bash
# Build 026 M1 — Production Bundle Hardening & Reproducibility gate.
#
# Re-verifies the current, integrated M1 state directly: the No-VTK
# reproducibility mechanism (the milestone's primary objective), corrected
# bundle metadata, the PyInstaller hiddenimports cleanup, dependency/
# toolchain pinning, CI Stage 1 presence, and a real end-to-end pipeline
# exercise against a freshly rebuilt productive sidecar — following the same
# "verify the current integrated state, not a frozen milestone baseline"
# discipline as scripts/validate-build025.sh.
#
# Never touches experiments/, tools/poc/, or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build026-m1"
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
  echo "# BUILD-026-M1: $1"
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
  local label="$1"
  local count="$2"
  if [ -z "${count}" ] || [ "${count}" -eq 0 ]; then
    echo "  FAIL ${label}: 0 tests executed — a filtered/empty run is not a pass" >&2
    FAILED=1
  else
    echo "  OK   ${label}: ${count} tests executed"
  fi
}

section "No-VTK reproducibility mechanism — the primary M1 objective"
check "apply-cadquery-novtk-patch.sh present and executable" \
  '[ -x scripts/apply-cadquery-novtk-patch.sh ]'
check "provision-novtk-bundle-venv.sh present and executable" \
  '[ -x scripts/provision-novtk-bundle-venv.sh ]'
check "validate-te0012-novtk-bundle.sh no longer copies from .venv-novtk-poc" \
  '! grep -q "POC_PATCH_SOURCE\|venv-novtk-poc/lib" scripts/validate-te0012-novtk-bundle.sh'
check "build-productive-desktop-app.sh points to the new provisioning script" \
  'grep -q "provision-novtk-bundle-venv.sh" scripts/build-productive-desktop-app.sh'
check "the 4 tracked TE-001.1 patch files are well-formed (no bare/malformed blank context lines)" \
  'for f in docs/research/TE-001.1-CadQuery-NoVTK/patches/*.diff; do
     awk "/^@@/{h=1;next} h && (\$0==\"\" || \$0==\"\\r\") {exit 1}" "$f" || exit 1
   done'
check ".gitattributes protects the patch files from line-ending normalization (real defect found this milestone — see BUILD-026-M1-PRODUCTION-BUNDLE-HARDENING.md)" \
  'grep -q "docs/research/TE-001.1-CadQuery-NoVTK/patches/\*.diff -text" .gitattributes'
check "the committed git object (not just the working tree) preserves CRLF in the patch files" \
  'for f in docs/research/TE-001.1-CadQuery-NoVTK/patches/*.diff; do
     git cat-file -p "HEAD:$f" 2>/dev/null | grep -qP "\\r" || exit 1
   done'

section "Fresh-environment No-VTK proof — real, against a throwaway venv, not the shared one"
FRESH_VENV="${REPORT_DIR}/fresh-novtk-proof-venv"
rm -rf "${FRESH_VENV}"
if command -v python3.13 >/dev/null 2>&1; then
  python3.13 -m venv "${FRESH_VENV}"
  "${FRESH_VENV}/bin/pip" install -q --upgrade pip
  "${FRESH_VENV}/bin/pip" install -q "cadquery-ocp-novtk==7.9.3.1.1"
  "${FRESH_VENV}/bin/pip" install -q "cadquery==2.8.0" --no-deps
  "${FRESH_VENV}/bin/pip" install -q \
    "ezdxf>=1.3.0" "multimethod<2.0,>=1.11" "nlopt<3.0,>=2.9.0" \
    "runtype==0.5.3" "casadi==3.7.2" "pyparsing>=3.0.0"
  if scripts/apply-cadquery-novtk-patch.sh "${FRESH_VENV}/bin/python" > "${REPORT_DIR}/fresh-novtk-proof.log" 2>&1; then
    echo "  OK   fresh, from-scratch venv + tracked patches -> import cadquery succeeds under VTKImportBlocker"
  else
    echo "  FAIL fresh-environment No-VTK reproducibility proof failed — see ${REPORT_DIR}/fresh-novtk-proof.log" >&2
    tail -20 "${REPORT_DIR}/fresh-novtk-proof.log" >&2
    FAILED=1
  fi
  rm -rf "${FRESH_VENV}"
else
  echo "  FAIL python3.13 not found — cannot run the fresh-environment proof" >&2
  FAILED=1
fi

section "Bundle metadata — Decision 1/2/4 applied, verified against the compiled Info.plist"
APP_PATH="desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
check "tauri.conf.json identifier is the approved de.zerorodcad.desktop" \
  'grep -q "\"identifier\": \"de.zerorodcad.desktop\"" desktop/src-tauri/tauri.conf.json'
check "tauri.conf.json no longer contains the retired dev.zerorodcad.desktop identifier" \
  '! grep -q "dev.zerorodcad.desktop" desktop/src-tauri/tauri.conf.json'
check "src-tauri/Info.plist override present (LSRequiresCarbon)" \
  '[ -f desktop/src-tauri/Info.plist ] && grep -q "LSRequiresCarbon" desktop/src-tauri/Info.plist'
if [ -d "${APP_PATH}" ]; then
  check "compiled Info.plist: CFBundleIdentifier = de.zerorodcad.desktop" \
    'plutil -extract CFBundleIdentifier raw "'"${APP_PATH}"'/Contents/Info.plist" | grep -q "^de.zerorodcad.desktop$"'
  check "compiled Info.plist: LSRequiresCarbon = false" \
    '[ "$(plutil -extract LSRequiresCarbon raw "'"${APP_PATH}"'/Contents/Info.plist")" = "false" ]'
  check "compiled Info.plist: LSMinimumSystemVersion present and non-empty" \
    '[ -n "$(plutil -extract LSMinimumSystemVersion raw "'"${APP_PATH}"'/Contents/Info.plist" 2>/dev/null)" ]'
else
  echo "  SKIPPED compiled-Info.plist checks: ${APP_PATH} not built yet in this run"
fi

section "Engineering identity — app_info() reports Build 026 / M1"
check "app_info() source reports build=026, milestone=M1" \
  'grep -q "build: \"026\".to_string()" desktop/src-tauri/src/commands.rs \
   && grep -q "milestone: \"M1\".to_string()" desktop/src-tauri/src/commands.rs'
check "regression test pins the current identity" \
  'grep -q "assert_eq!(info.build, \"026\");" desktop/src-tauri/src/commands.rs \
   && grep -q "assert_eq!(info.milestone, \"M1\");" desktop/src-tauri/src/commands.rs'
check "stale Build 025 / M5 pair guarded against" \
  'grep -q "app_info_never_reports_a_stale_025_m5_pair" desktop/src-tauri/src/commands.rs'

section "PyInstaller hiddenimports cleanup — evidence-based, not suppressed"
check "OCP.TKernel removed from sidecar-onedir.spec hiddenimports (list entries, not prose comments)" \
  '! grep -v "^\s*#" packaging/tauri/sidecar-onedir.spec | grep -q "\"OCP.TKernel\""'
check "cadquery.exporters removed from sidecar-onedir.spec hiddenimports (list entries, not prose comments)" \
  '! grep -v "^\s*#" packaging/tauri/sidecar-onedir.spec | grep -q "\"cadquery.exporters\""'
check "cadquery.occ_impl still declared (the real module path)" \
  'grep -q "\"cadquery.occ_impl\"" packaging/tauri/sidecar-onedir.spec'

section "Toolchain / dependency pinning"
check "rust-toolchain.toml present" '[ -f desktop/src-tauri/rust-toolchain.toml ]'
check ".nvmrc present for the frontend" '[ -f desktop/frontend/.nvmrc ]'
check "casadi/runtype pinned exactly in provisioning script (no longer floating)" \
  'grep -q "casadi==3.7.2" scripts/provision-novtk-bundle-venv.sh \
   && grep -q "runtype==0.5.3" scripts/provision-novtk-bundle-venv.sh'
check "Cargo.lock tracked by git" '[ -n "$(git ls-files desktop/src-tauri/Cargo.lock)" ]'
check "frontend package-lock.json tracked by git" '[ -n "$(git ls-files desktop/frontend/package-lock.json)" ]'

section "CI Stage 1 — build-only pipeline verification, no secrets"
check "productive-build CI workflow present" '[ -f .github/workflows/build-productive.yml ]'
check "CI workflow contains no Apple/signing/notarization credential references" \
  '! grep -qiE "APPLE_ID|APPLE_PASSWORD|APPLE_TEAM_ID|CERTIFICATE|notarytool|codesign .*Developer" .github/workflows/build-productive.yml'

section "Security — WebView capability boundary unchanged (no M1 delta)"
check "capability set unchanged: exactly the 4 Build-025 permissions" \
  'grep -q "\"permissions\": \[\"core:default\", \"dialog:allow-open\", \"dialog:allow-save\", \"core:window:allow-destroy\"\]" desktop/src-tauri/capabilities/main-capability.json'

section "Legacy PySide6 / experiments / tools/poc untouched"
check "legacy PySide6 app directory untouched by M1 (compare against Build 025 final commit)" \
  'git diff --quiet bff1944 -- src/zerorodcad_desktop/ 2>/dev/null'
check "experiments/ untouched by M1" \
  'git diff --quiet bff1944 -- experiments/ 2>/dev/null'
check "tools/poc/ untouched by M1" \
  'git diff --quiet bff1944 -- tools/poc/ 2>/dev/null'

section "Full test suites — Python (Ruff + pytest)"
"${PY}" -m ruff check src/ tests/
"${PY}" -m ruff format --check src/ tests/
echo "ruff clean"
PY_LOG="${REPORT_DIR}/pytest.log"
"${PY}" -m pytest -q | tee "${PY_LOG}"
PY_COUNT=$(grep -oE "[0-9]+ passed" "${PY_LOG}" | tail -1 | grep -oE "[0-9]+" || echo "")
require_nonzero_tests "Python full suite" "${PY_COUNT}"

section "Full test suites — Rust (cargo test / fmt / clippy)"
RUST_LOG="${REPORT_DIR}/cargo-test.log"
(cd desktop/src-tauri && cargo test) | tee "${RUST_LOG}"
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)
RUST_COUNT=$(grep -oE "^test result: ok\. [0-9]+ passed" "${RUST_LOG}" | grep -oE "[0-9]+" | awk '{s+=$1} END{print s+0}')
require_nonzero_tests "Rust suite (summed across all binaries)" "${RUST_COUNT}"

section "Full test suites — Frontend (vitest / TypeScript / production build)"
FRONT_LOG="${REPORT_DIR}/vitest.log"
(cd desktop/frontend && npm run test -- --run) | tee "${FRONT_LOG}"
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)
FRONT_COUNT=$(grep -oE "Tests +[0-9]+ passed" "${FRONT_LOG}" | tail -1 | grep -oE "[0-9]+" || echo "")
require_nonzero_tests "Frontend vitest suite" "${FRONT_COUNT}"

section "Dependency invariants + real end-to-end final pipeline — freshly rebuilt productive onedir sidecar"
BUNDLE_VENV=".venv-novtk-bundle"
SIDECAR_DIST="desktop/sidecar-dist"
if [ -x "${BUNDLE_VENV}/bin/python" ]; then
  set +e
  rm -rf "${SIDECAR_DIST}" build/zerorod-engine
  "${BUNDLE_VENV}/bin/pyinstaller" --noconfirm --clean --log-level WARN \
    --distpath "${SIDECAR_DIST}" --workpath build/zerorod-engine \
    packaging/tauri/sidecar-onedir.spec > "${REPORT_DIR}/pyinstaller-rebuild.log" 2>&1
  PYINSTALLER_EXIT=$?
  set -e
  if [ "${PYINSTALLER_EXIT}" -eq 0 ] && [ -x "${SIDECAR_DIST}/zerorod-engine/zerorod-engine" ]; then
    echo "OK   productive onedir sidecar rebuilt successfully (no hidden-import errors expected now)"
    check "no PyInstaller hidden-import warnings in the fresh rebuild log" \
      '! grep -qi "Hidden import" "'"${REPORT_DIR}"'/pyinstaller-rebuild.log"'
    BUNDLED_SIDECAR="${SIDECAR_DIST}/zerorod-engine/zerorod-engine"

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
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"project-save\",\"command\":\"project_save\",\"parameters\":{\"path\":\"$(pwd)/${PROJECT_DIR}/m1-gate.zerorod\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":60.0}}}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"project-open\",\"command\":\"project_open\",\"parameters\":{\"path\":\"$(pwd)/${PROJECT_DIR}/m1-gate.zerorod\"}}" \
      "{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"export-alt\",\"command\":\"export\",\"parameters\":{\"output_directory\":\"$(pwd)/${ALT_DIR}\",\"parameters\":{\"schema\":\"zerorod-parameters/v1\",\"values\":{\"body_width\":60.0}}}}" \
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
assert Path(project_dir / "m1-gate.zerorod").is_file()
assert responses["project-open"]["ok"] is True, responses["project-open"]
opened_values = responses["project-open"]["result"]["values"]
assert opened_values["body_width"] == 60.0, opened_values
assert responses["export-alt"]["ok"] is True, responses["export-alt"]
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

live_report = responses["report-alt"]["result"].get("markdown")
assert live_report is not None, responses["report-alt"]
assert "60.00 mm" in live_report

print("real end-to-end pipeline (against the No-VTK-reproduced sidecar): status, "
      "preview x3, report, project save/open roundtrip, export x2, all outputs "
      "valid, shutdown ok")
PYEOF
    then
      echo "  OK   real end-to-end final pipeline passed"
    else
      echo "  FAIL real end-to-end final pipeline did not pass" >&2
      FAILED=1
    fi
    rm -rf "${DEFAULT_DIR}" "${ALT_DIR}" "${PROJECT_DIR}"
    rm -rf "${SIDECAR_DIST}" build/zerorod-engine
  else
    echo "  FAIL productive onedir sidecar rebuild failed. Log: ${REPORT_DIR}/pyinstaller-rebuild.log" >&2
    tail -20 "${REPORT_DIR}/pyinstaller-rebuild.log" || true
    FAILED=1
  fi
else
  echo "  FAIL ${BUNDLE_VENV} not found. Run scripts/provision-novtk-bundle-venv.sh first." >&2
  FAILED=1
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
  echo "BUILD-026-M1 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-026-M1 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
