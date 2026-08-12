#!/usr/bin/env bash
# Build 023 / Milestone 1 — Parameter Model & Request Contract Foundation
# validation gate.
#
# Rebuilds the productive onedir sidecar (same spec as Build 022, now
# containing the M1 zerorod-parameters/v1 changes) and proves the parameter
# contract end to end against the real binary, then runs the full
# Python/Rust/TypeScript regression suite and the Build 022 master gate to
# confirm the Build 022 baseline is still intact. Never touches
# experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build023-m1"
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
  echo "# BUILD-023-M1: $1"
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
check "Parameter discovery report present" \
  '[ -f docs/migration/BUILD-023-M1-PARAMETER-DISCOVERY.md ]'
check "Parameter contract spec present" \
  '[ -f docs/contracts/ZEROROD-PARAMETERS-V1.md ]'
check "M1 implementation record present" \
  '[ -f docs/migration/BUILD-023-M1-PARAMETER-CONTRACT.md ]'

section "Python — Ruff / format"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
echo "ruff clean"

section "Python — sidecar / parameter contract unit tests"
"${PY}" -m pytest \
  tests/test_zerorod_sidecar_protocol.py \
  tests/test_zerorod_sidecar_mesh_contract.py \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  tests/test_zerorod_sidecar_parameters_contract.py \
  tests/test_parameters.py \
  tests/test_validation.py \
  -v

section "Python — No-VTK real subprocess (TE-001.1-patched interpreter)"
if [ -x ".venv-novtk-poc/bin/python" ]; then
  "${PY}" -m pytest tests/test_zerorod_sidecar_persistent.py::TestRealPersistentSubprocess -v
else
  echo "SKIPPED: .venv-novtk-poc not present"
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

section "Security — WebView capability and CSP unchanged"
check "capability grants only core:default" \
  'grep -q "\"permissions\": \[\"core:default\"\]" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP matches the M1-M4 restrictive baseline" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'

section "Packaging — rebuild the productive onedir sidecar (M1 code included)"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"
SIDECAR_DIST="desktop/sidecar-dist"
if [ -x "${BUNDLE_PYTHON}" ]; then
  rm -rf "${SIDECAR_DIST}" build/zerorod-engine
  "${BUNDLE_VENV}/bin/pyinstaller" --noconfirm --clean --log-level WARN \
    --distpath "${SIDECAR_DIST}" --workpath build/zerorod-engine \
    packaging/tauri/sidecar-onedir.spec
  BUNDLED_SIDECAR="${SIDECAR_DIST}/zerorod-engine/zerorod-engine"
  check "bundled sidecar binary produced" "[ -x '${BUNDLED_SIDECAR}' ]"

  echo "== no VTK/PySide6/Qt in the freshly built sidecar =="
  for pat in "*vtk*" "*pyside*" "*[Qq]t*"; do
    matches=$(find "${SIDECAR_DIST}" -iname "${pat}" 2>/dev/null | grep -v "cadquery_ocp_novtk" || true)
    if [ -n "${matches}" ]; then
      echo "unexpected match for '${pat}': ${matches}" >&2
      FAILED=1
    fi
  done
  echo "0 VTK/PySide6/Qt files in ${SIDECAR_DIST}"

  section "Real pipeline — explicit-default / alternate-parameter / invalid / valid-after-invalid"
  printf '%s\n' \
    '{"schema":"zerorod-sidecar/v1","request_id":"A","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"B","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"project_name":"CBG Open G","body_width":38.0,"body_depth":9.0,"fretboard_height":6.9,"rod_diameter":3.0,"groove_diameter":2.94,"rod_center_z_offset":-0.75,"groove_front_clearance":0.01,"string_gauges_inch":[0.036,0.026,0.017],"string_spacing":10.0,"string_inlet_y":0.0,"string_inlet_z":2.8,"channel_diameter":1.15,"channel_overrun_at_inlet":0.8,"channel_rod_clearance":0.05,"minimum_wall":1.2}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"C","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"body_width":60.0,"string_spacing":12.0}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"D","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"groove_diameter":5.0,"rod_diameter":3.0}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"E","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"F","command":"preview","parameters":{"schema":"not-a-real-schema","values":{}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"G","command":"shutdown"}' \
    | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/real-integration.jsonl"

  "${PY}" - "${REPORT_DIR}/real-integration.jsonl" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    responses = {json.loads(l)["request_id"]: json.loads(l) for l in f if l.strip()}

a, b, c, d, e, f, g = (responses[k] for k in "ABCDEFG")

assert a["ok"] and a["result"]["schema"] == "zerorod-mesh/v1", a
assert b["ok"], b
assert a["result"]["bounds"] == b["result"]["bounds"], "A/B bounds must match"
assert [m["positions"] for m in a["result"]["meshes"]] == [m["positions"] for m in b["result"]["meshes"]]
print("A vs B (explicit-default equivalence): PASS")

assert c["ok"], c
a_extent = a["result"]["bounds"]["max"][0] - a["result"]["bounds"]["min"][0]
c_extent = c["result"]["bounds"]["max"][0] - c["result"]["bounds"]["min"][0]
assert c_extent > a_extent, (a_extent, c_extent)
print(f"C (alternate valid parameters): PASS — X extent {a_extent:.3f} -> {c_extent:.3f} mm")

assert not d["ok"] and d["error"]["code"] == "invalid_parameters_domain", d
print("D (invalid cross-parameter combination): PASS")

assert e["ok"] and e["result"]["schema"] == "zerorod-mesh/v1", e
print("E (valid-after-invalid, same process): PASS")

assert not f["ok"] and f["error"]["code"] == "invalid_parameters_schema", f
print("F (unknown parameters schema): PASS")

assert g["ok"] and g["result"]["status"] == "shutting_down", g
print("G (shutdown): PASS")
PY

  echo "== 0 orphan processes after the subprocess above exited =="
  if pgrep -f "zerorod-engine-onedir/zerorod-engine\|sidecar-dist/zerorod-engine/zerorod-engine" >/dev/null 2>&1; then
    echo "orphan zerorod-engine process(es) found" >&2
    pgrep -fl "zerorod-engine" >&2
    FAILED=1
  fi
  echo "0 orphan processes"
else
  echo "SKIPPED (real pipeline / packaging checks): ${BUNDLE_VENV} not found. Run" \
    "scripts/validate-te0012-novtk-bundle.sh first to provision it."
fi

section "Build 022 regression gate (must remain PASS)"
if ./scripts/validate-build022.sh; then
  echo "BUILD-022 CONSISTENCY GATE: PASS (re-confirmed)"
else
  echo "BUILD-022 CONSISTENCY GATE: FAIL — Build 023 M1 cannot PASS" >&2
  FAILED=1
fi

section "Repository — experiments/te002-tauri and legacy PySide6 unchanged"
check "experiments/te002-tauri unchanged" \
  'git diff --quiet -- experiments/te002-tauri/ 2>/dev/null'
check "legacy PySide6 app unchanged" \
  'git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null'

echo ""
echo "########################################################################"
if [ "${FAILED}" -eq 0 ]; then
  echo "BUILD-023-M1 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-023-M1 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
