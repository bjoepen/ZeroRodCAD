#!/usr/bin/env bash
# Build 023 / Milestone 4 — Live Preview Behavior & UX validation gate.
#
# M4 required no backend (Rust/Python) source changes — the parameterized
# preview path was already built and tested in M1, and M3 already proved
# the manual Apply request shape end to end
# (docs/migration/BUILD-023-M4-LIVE-PREVIEW.md). This script re-runs the
# Build-023-M3 gate (which itself re-confirms M2, M1, and Build-022
# internally) to prove nothing regressed, runs the M4-specific frontend
# scheduling tests explicitly, then proves the real request shape against
# the freshly rebuilt productive onedir sidecar: a repeated alternating
# parameter sequence (the same body_width 38<->60mm case M1/M3 already
# proved, exercised repeatedly), a gauge change, and a 20-request
# RSS/timing check reusing TE-002.1's existing benchmark tool. Never
# touches experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build023-m4"
mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3.13"
fi

M1_BASELINE_COMMIT="2ac88d6"

FAILED=0
section() {
  echo ""
  echo "########################################################################"
  echo "# BUILD-023-M4: $1"
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
check "M4 implementation record present" \
  '[ -f docs/migration/BUILD-023-M4-LIVE-PREVIEW.md ]'
check "M4 human validation checklist present" \
  '[ -f docs/migration/BUILD-023-M4-HUMAN-VALIDATION.md ]'
check "M3 human validation record updated" \
  'grep -q "Result | \*\*PASS\*\*" docs/migration/BUILD-023-M3-HUMAN-VALIDATION.md'
check "live_preview.ts present" \
  '[ -f desktop/frontend/src/live_preview.ts ]'

section "Build-023-M3 gate (re-confirms M2, M1, Build-022 internally — must remain PASS)"
if ./scripts/validate-build023-m3.sh; then
  echo "BUILD-023-M3 CONSISTENCY GATE: PASS (re-confirmed)"
else
  echo "BUILD-023-M3 CONSISTENCY GATE: FAIL — Build 023 M4 cannot PASS" >&2
  FAILED=1
fi

section "Frontend — M4 scheduling/live-preview tests (explicit)"
(cd desktop/frontend && npx vitest run \
  src/live_preview.test.ts \
  src/parameter_panel.test.ts \
  src/scene.test.ts \
  src/parameter_state.test.ts)

section "Frontend — full vitest / TypeScript / build (M1-M4 combined)"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)
echo "frontend dist size (informational):"
du -sh desktop/frontend/dist 2>/dev/null || echo "dist/ not found"

section "Rust — cargo test / fmt / clippy (unchanged by M4, must remain clean)"
(cd desktop/src-tauri && cargo test)
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)

section "Python — Ruff / full repository regression suite (unchanged by M4, must remain clean)"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
"${PY}" -m pytest -q

section "Repository — Rust/Python backend unchanged by M4 (frontend-only milestone)"
check "no Rust source changes vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- desktop/src-tauri/src/ 2>/dev/null"
check "no Python engine/sidecar source changes vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- src/zerorod_sidecar/ src/zerorodcad/ 2>/dev/null"

section "Contracts unchanged (§54 of the mandate)"
check "zerorod-parameters/v1 contract doc unchanged vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- docs/contracts/ZEROROD-PARAMETERS-V1.md 2>/dev/null"
check "mesh contract module unchanged vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- src/zerorod_sidecar/mesh_contract.py desktop/frontend/src/mesh.ts desktop/src-tauri/src/mesh.rs 2>/dev/null"
check "sidecar protocol module unchanged vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- src/zerorod_sidecar/protocol.py desktop/src-tauri/src/protocol.rs 2>/dev/null"

section "Security — WebView capability and CSP unchanged"
check "capability grants only core:default" \
  'grep -q "\"permissions\": \[\"core:default\"\]" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP matches the M1-M4 restrictive baseline" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'

section "Packaging — rebuild the productive onedir sidecar (fresh, for the real-pipeline proof below)"
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

  echo "== 0 VTK/PySide6/Qt/numba/llvmlite/scipy in the freshly built sidecar =="
  for pat in "*vtk*" "*pyside*" "*[Qq]t*" "*numba*" "*llvmlite*" "*scipy*"; do
    matches=$(find "${SIDECAR_DIST}" -iname "${pat}" 2>/dev/null | grep -v "cadquery_ocp_novtk" || true)
    if [ -n "${matches}" ]; then
      echo "unexpected match for '${pat}': ${matches}" >&2
      FAILED=1
    fi
  done
  echo "0 VTK/PySide6/Qt/numba/llvmlite/scipy files in ${SIDECAR_DIST}"

  section "Real pipeline — repeated live-preview-shaped sequence (38 -> 45 -> 60 -> 38, gauge change)"
  printf '%s\n' \
    '{"schema":"zerorod-sidecar/v1","request_id":"A","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"B","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"body_width":45.0}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"C","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"body_width":60.0}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"D","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"body_width":38.0}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"E","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"string_gauges_inch":[0.036,0.048,0.017]}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"F","command":"preview","parameters":{"schema":"zerorod-parameters/v1","values":{"body_width":60.0}}}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"G","command":"shutdown"}' \
    | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/real-live-preview-sequence.jsonl"

  "${PY}" - "${REPORT_DIR}/real-live-preview-sequence.jsonl" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    responses = {json.loads(l)["request_id"]: json.loads(l) for l in f if l.strip()}

a, b, c, d, e, f, g = (responses[k] for k in "ABCDEFG")

def x_extent(resp):
    bounds = resp["result"]["bounds"]
    return bounds["max"][0] - bounds["min"][0]

for label, resp in [("A", a), ("B", b), ("C", c), ("D", d), ("E", e), ("F", f)]:
    assert resp["ok"], (label, resp)

default_extent = x_extent(a)
assert abs(default_extent - 38.0) < 1.0, default_extent
assert abs(x_extent(d) - default_extent) < 0.01, "D (back to 38) must match A"
assert x_extent(c) > x_extent(b) > default_extent, "45 -> 60 must monotonically widen"
print(f"A/B/C/D (38 -> 45 -> 60 -> 38): PASS — extents "
      f"{x_extent(a):.3f} -> {x_extent(b):.3f} -> {x_extent(c):.3f} -> {x_extent(d):.3f} mm")

assert e["ok"], e
print("E (gauge change mid-sequence): PASS")

assert abs(x_extent(f) - x_extent(c)) < 0.01, "F (60 again) must reproduce C's geometry, no stale state"
print("F (repeated identical request after intervening ones): PASS — no stale-state corruption")

assert g["ok"] and g["result"]["status"] == "shutting_down", g
print("G (shutdown after 6 sequential varied requests, same process): PASS")
PY

  echo "== 0 orphan processes after the subprocess above exited =="
  if pgrep -f "zerorod-engine-onedir/zerorod-engine\|sidecar-dist/zerorod-engine/zerorod-engine" >/dev/null 2>&1; then
    echo "orphan zerorod-engine process(es) found" >&2
    pgrep -fl "zerorod-engine" >&2
    FAILED=1
  fi
  echo "0 orphan processes"

  section "Memory / performance — 20 sequential persistent requests (reusing TE-002.1's benchmark tool)"
  "${PY}" tools/poc/tauri/benchmark_sidecar_runtime.py persistent \
    --binary "${BUNDLED_SIDECAR}" --requests 20 \
    --output "${REPORT_DIR}/memory-benchmark.json"
  "${PY}" - "${REPORT_DIR}/memory-benchmark.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
checkpoints = data["rss_kb_by_checkpoint"]
print(f"RSS by checkpoint (KB): {checkpoints}")
values = [v for v in checkpoints.values() if v is not None]
if len(values) >= 2:
    growth_pct = (values[-1] - values[0]) / values[0] * 100
    print(f"RSS growth over {data['requests_requested']} requests: {growth_pct:.2f}%")
    assert growth_pct < 25.0, f"unexpected RSS growth: {growth_pct:.2f}%"
warm_median = data["warm_roundtrip_seconds"]["median"]
debounce_s = 0.300
print(f"engine warm median: {warm_median:.4f}s, p95: {data['warm_roundtrip_seconds']['p95']:.4f}s "
      f"(M1 baseline: ~0.121-0.125s)")
print(f"debounce: {debounce_s:.3f}s (fixed, LIVE_PREVIEW_DEBOUNCE_MS)")
print(f"approximate perceived stable-edit -> preview latency: {debounce_s + warm_median:.3f}s")
PY
else
  echo "SKIPPED (real pipeline / packaging / memory checks): ${BUNDLE_VENV} not found. Run" \
    "scripts/validate-te0012-novtk-bundle.sh first to provision it."
fi

section "Repository — experiments/te002-tauri and legacy PySide6 unchanged"
check "experiments/te002-tauri unchanged" \
  'git diff --quiet -- experiments/te002-tauri/ 2>/dev/null'
check "legacy PySide6 app unchanged" \
  'git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null'

echo ""
echo "########################################################################"
if [ "${FAILED}" -eq 0 ]; then
  echo "BUILD-023-M4 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-023-M4 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
