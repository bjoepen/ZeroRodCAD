#!/usr/bin/env bash
# Build 023 / Milestone 2 — Parameter Controls Foundation validation gate.
#
# M2 is a frontend-only milestone (no Rust/Python source changes — see
# docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md). This script re-runs
# the Build-023-M1 gate (which itself re-confirms the Build-022 gate) to
# prove neither regressed, runs the M2-specific frontend test files
# explicitly, then the full frontend/Rust/Python regression suite, then the
# same packaging/security/repository invariants the earlier gates check.
# Never touches experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build023-m2"
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
  echo "# BUILD-023-M2: $1"
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
check "M2 implementation record present" \
  '[ -f docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md ]'
check "M2 human validation checklist present" \
  '[ -f docs/migration/BUILD-023-M2-HUMAN-VALIDATION.md ]'
check "parameter_metadata.ts present" \
  '[ -f desktop/frontend/src/parameter_metadata.ts ]'
check "parameter_state.ts present" \
  '[ -f desktop/frontend/src/parameter_state.ts ]'
check "parameter_panel.ts present" \
  '[ -f desktop/frontend/src/parameter_panel.ts ]'

section "Build-023-M1 gate (re-confirms Build-022 internally — must remain PASS)"
if ./scripts/validate-build023-m1.sh; then
  echo "BUILD-023-M1 CONSISTENCY GATE: PASS (re-confirmed)"
else
  echo "BUILD-023-M1 CONSISTENCY GATE: FAIL — Build 023 M2 cannot PASS" >&2
  FAILED=1
fi

section "Frontend — M2 parameter modules (explicit)"
(cd desktop/frontend && npx vitest run \
  src/parameter_metadata.test.ts \
  src/parameter_state.test.ts \
  src/parameter_panel.test.ts)

section "Frontend — no automatic preview IPC on parameter edit (explicit re-check)"
# A `vitest -t` filter that matches zero tests still exits 0 ("skipped", not
# "failed") — silently vacuous if the matching test is ever renamed (as it
# was in Build 023 M3, when this suite's Apply flow moved from local-only to
# engine-connected and the describe/it titles changed). Guarded explicitly
# below so a future rename fails loudly here instead of silently no-op'ing.
M2_IPC_CHECK_OUTPUT=$(cd desktop/frontend && npx vitest run src/parameter_panel.test.ts -t "never calls applyParameters" 2>&1)
echo "${M2_IPC_CHECK_OUTPUT}"
if ! echo "${M2_IPC_CHECK_OUTPUT}" | grep -qE "Tests {2}[1-9][0-9]* passed"; then
  echo "FAIL: expected at least 1 passing test matching the Apply-flow name filter, got 0 (was the test renamed?)" >&2
  FAILED=1
fi

section "Frontend — full vitest / TypeScript / build (M1 + M2 combined)"
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)
echo "frontend dist size (informational — a small increase over the M1 baseline is expected/acceptable):"
du -sh desktop/frontend/dist 2>/dev/null || echo "dist/ not found"

section "Rust — cargo test / fmt / clippy (unchanged by M2, must remain clean)"
(cd desktop/src-tauri && cargo test)
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)

section "Python — Ruff / full repository regression suite (unchanged by M2, must remain clean)"
"${PY}" -m ruff check src/zerorod_sidecar/ tests/
"${PY}" -m ruff format --check src/zerorod_sidecar/ tests/
"${PY}" -m pytest -q

section "Repository — Rust/Python backend unchanged by M2 (frontend-only milestone, §39 of the mandate)"
check "no Rust source changes vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- desktop/src-tauri/src/ 2>/dev/null"
check "no Python engine/sidecar source changes vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- src/zerorod_sidecar/ src/zerorodcad/ 2>/dev/null"

section "Security — WebView capability and CSP unchanged"
check "capability grants only core:default" \
  'grep -q "\"permissions\": \[\"core:default\"\]" desktop/src-tauri/capabilities/main-capability.json'
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
check "CSP matches the M1-M4 restrictive baseline" \
  "grep -qF \"${EXPECTED_CSP}\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'

section "Packaging invariants (bundle produced by the Build-023-M1 gate above)"
SIDECAR_DIST="desktop/sidecar-dist"
if [ -x "${SIDECAR_DIST}/zerorod-engine/zerorod-engine" ]; then
  for pat in "*vtk*" "*pyside*" "*[Qq]t*" "*numba*" "*llvmlite*" "*scipy*"; do
    matches=$(find "${SIDECAR_DIST}" -iname "${pat}" 2>/dev/null | grep -v "cadquery_ocp_novtk" || true)
    if [ -n "${matches}" ]; then
      echo "unexpected match for '${pat}': ${matches}" >&2
      FAILED=1
    fi
  done
  echo "0 VTK/PySide6/Qt/numba/llvmlite/scipy files in ${SIDECAR_DIST}"
else
  echo "SKIPPED: no bundled sidecar found at ${SIDECAR_DIST} (the M1 gate's own packaging section" \
    "reports SKIPPED when .venv-novtk-bundle is absent — see its output above)"
fi

section "Repository — experiments/te002-tauri and legacy PySide6 unchanged"
check "experiments/te002-tauri unchanged" \
  'git diff --quiet -- experiments/te002-tauri/ 2>/dev/null'
check "legacy PySide6 app unchanged" \
  'git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null'

echo ""
echo "########################################################################"
if [ "${FAILED}" -eq 0 ]; then
  echo "BUILD-023-M2 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-023-M2 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
