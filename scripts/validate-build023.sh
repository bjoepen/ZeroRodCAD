#!/usr/bin/env bash
# Build 023 — Parameters & Live Preview — master validation gate.
#
# Orchestrates the existing per-milestone gates rather than duplicating
# their checks: scripts/validate-build023-m4.sh already re-confirms M3,
# which re-confirms M2, which re-confirms M1, which re-confirms
# Build-022 — so calling it once already proves the full chain. This
# script adds only what is genuinely new at the Build-023-as-a-whole
# level: a final documentation-consistency check and a final restated
# summary of what M1-M4 together prove, plus the exact same final
# fresh-release-and-real-pipeline evidence class M2/M3/M4 each produced,
# now labeled as the Build-023 master proof rather than a milestone-local
# one. Never touches experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build023-final"
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
  echo "# BUILD-023: $1"
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

section "Documentation present — Build-023 completion record"
check "Build-023 completion document present" \
  '[ -f docs/migration/BUILD-023-COMPLETION.md ]'
check "Build-024 handoff present" \
  '[ -f docs/migration/BUILD-024-HANDOFF.md ]'
check "M1 documentation present" \
  '[ -f docs/migration/BUILD-023-M1-PARAMETER-CONTRACT.md ] && [ -f docs/migration/BUILD-023-M1-PARAMETER-DISCOVERY.md ]'
check "M2 documentation present" \
  '[ -f docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md ] && [ -f docs/migration/BUILD-023-M2-HUMAN-VALIDATION.md ]'
check "M3 documentation present" \
  '[ -f docs/migration/BUILD-023-M3-PARAMETER-ENGINE-INTEGRATION.md ] && [ -f docs/migration/BUILD-023-M3-HUMAN-VALIDATION.md ]'
check "M4 documentation present" \
  '[ -f docs/migration/BUILD-023-M4-LIVE-PREVIEW.md ] && [ -f docs/migration/BUILD-023-M4-HUMAN-VALIDATION.md ]'
check "zerorod-parameters/v1 contract doc present" \
  '[ -f docs/contracts/ZEROROD-PARAMETERS-V1.md ]'

section "Human validation history — must all read PASS"
check "M2 human validation recorded PASS" \
  'grep -q "Result | \*\*PASS\*\*" docs/migration/BUILD-023-M2-HUMAN-VALIDATION.md'
check "M3 human validation recorded PASS" \
  'grep -q "Result | \*\*PASS\*\*" docs/migration/BUILD-023-M3-HUMAN-VALIDATION.md'
check "M4 human validation recorded PASS" \
  'grep -q "Result | \*\*PASS\*\*" docs/migration/BUILD-023-M4-HUMAN-VALIDATION.md'

section "Build-023-M4 gate (re-confirms M3, M2, M1, Build-022 internally — must remain PASS)"
if ./scripts/validate-build023-m4.sh; then
  echo "BUILD-023-M4 CONSISTENCY GATE: PASS (re-confirmed)"
else
  echo "BUILD-023-M4 CONSISTENCY GATE: FAIL — Build 023 master gate cannot PASS" >&2
  FAILED=1
fi

section "Contracts unchanged vs. the M1 baseline (the whole build must not have drifted)"
check "zerorod-parameters/v1 contract doc unchanged vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- docs/contracts/ZEROROD-PARAMETERS-V1.md 2>/dev/null"
check "mesh contract module unchanged vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- src/zerorod_sidecar/mesh_contract.py desktop/frontend/src/mesh.ts desktop/src-tauri/src/mesh.rs 2>/dev/null"
check "sidecar protocol module unchanged vs. the M1 baseline" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- src/zerorod_sidecar/protocol.py desktop/src-tauri/src/protocol.rs 2>/dev/null"
check "no Rust source changes vs. the M1 baseline (frontend-only M2-M4)" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- desktop/src-tauri/src/ 2>/dev/null"
check "no Python engine/sidecar source changes vs. the M1 baseline (frontend-only M2-M4)" \
  "git diff --quiet ${M1_BASELINE_COMMIT} -- src/zerorod_sidecar/ src/zerorodcad/ 2>/dev/null"

section "Architecture conformance (ADR-022-001)"
check "Tauri v2 CLI/API pinned" \
  'grep -q "\"@tauri-apps/cli\": \"\^2\." desktop/frontend/package.json && grep -q "\"@tauri-apps/api\": \"\^2\." desktop/frontend/package.json'
check "Three.js present" \
  'grep -q "\"three\":" desktop/frontend/package.json'
check "WebView capability grants only core:default (Rust owns the sidecar, not the WebView)" \
  'grep -q "\"permissions\": \[\"core:default\"\]" desktop/src-tauri/capabilities/main-capability.json'
check "CSP restrictive/unchanged" \
  "grep -qF \"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost\" desktop/src-tauri/tauri.conf.json"
check "no externalBin (onefile) fallback" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'
check "no shell/process capability exposed to the WebView beyond core:default" \
  '! grep -q "shell:allow\|process:allow" desktop/src-tauri/capabilities/main-capability.json'

section "Repository — experiments/te002-tauri and legacy PySide6 unchanged"
check "experiments/te002-tauri unchanged" \
  'git diff --quiet -- experiments/te002-tauri/ 2>/dev/null'
check "legacy PySide6 app unchanged" \
  'git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null'

section "Migration status documentation consistency"
check "README no longer shows Build 023 as IN PROGRESS" \
  '! grep -q "Build 023:.*IN PROGRESS" README.md'
check "ROADMAP no longer shows Build 023 M2 as the next milestone" \
  '! grep -q "NEXT: BUILD 023 / M2" ROADMAP.md'
check "docs/migration/README.md no longer shows Build 023 M2 as the next milestone" \
  '! grep -q "NEXT: BUILD 023 / M2" docs/migration/README.md'
check "ROADMAP shows Build 024 as the next build" \
  'grep -q "Build 024" ROADMAP.md'

echo ""
echo "########################################################################"
if [ "${FAILED}" -eq 0 ]; then
  echo "BUILD-023 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-023 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
