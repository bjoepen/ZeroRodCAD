#!/usr/bin/env bash
# Build 022 — master consistency gate (Milestone 5).
#
# Orchestrates the existing per-milestone gates (M2/M3/M4 — M1 has no
# separate script; its checks are a subset of what M2's frontend/Rust
# checks already re-exercise) rather than duplicating their logic, then
# adds the Build-022-wide checks that don't belong to any single
# milestone: architecture conformance against ADR-022-001, and a final
# release-build inventory. Never touches experiments/te002-tauri or the
# legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build022-m5"
mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3.13"
fi

FAILED=0
run_gate() {
  local name="$1"
  local script="$2"
  echo ""
  echo "########################################################################"
  echo "# BUILD-022 master gate: running ${name}"
  echo "########################################################################"
  if "${script}"; then
    echo "${name}: PASS"
  else
    echo "${name}: FAIL" >&2
    FAILED=1
  fi
}

run_gate "Milestone 2 (Productive Sidecar & Rust Lifecycle)" "./scripts/validate-build022-m2.sh"
run_gate "Milestone 3 (Three.js Preview Foundation)" "./scripts/validate-build022-m3.sh"
run_gate "Milestone 4 (Productive Packaging Baseline)" "./scripts/validate-build022-m4.sh"

echo ""
echo "########################################################################"
echo "# BUILD-022 master gate: architecture conformance (ADR-022-001)"
echo "########################################################################"

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

check "Tauri v2 dependency declared" \
  'grep -q "tauri = { version = \"2\"" desktop/src-tauri/Cargo.toml'
check "Three.js dependency declared" \
  'grep -q "\"three\"" desktop/frontend/package.json'
check "WebView never imports the shell plugin directly" \
  '! grep -rq "plugin-shell" desktop/frontend/src/*.ts 2>/dev/null'
check "Rust owns the persistent sidecar (engine.rs exists)" \
  '[ -f desktop/src-tauri/src/engine.rs ]'
check "WebView capability is core:default only" \
  'grep -q "\"permissions\": \[\"core:default\"\]" desktop/src-tauri/capabilities/main-capability.json'
check "zerorod-sidecar/v1 present in Python sidecar" \
  'grep -q "zerorod-sidecar/v1" src/zerorod_sidecar/protocol.py'
check "zerorod-sidecar/v1 present in Rust" \
  'grep -q "zerorod-sidecar/v1" desktop/src-tauri/src/protocol.rs'
check "zerorod-mesh/v1 present in Python sidecar" \
  'grep -q "zerorod-mesh/v1" src/zerorod_sidecar/mesh_contract.py'
check "zerorod-mesh/v1 present in Rust" \
  'grep -q "zerorod-mesh/v1" desktop/src-tauri/src/mesh.rs'
check "zerorod-mesh/v1 present in frontend" \
  'grep -q "zerorod-mesh/v1" desktop/frontend/src/mesh.ts'
check "no onefile fallback (externalBin) in tauri.conf.json" \
  '! grep -q "externalBin" desktop/src-tauri/tauri.conf.json'
check "onedir-only sidecar packaging spec" \
  'grep -q "COLLECT" packaging/tauri/sidecar-onedir.spec'
check "hash-gated dylib dedup script present" \
  '[ -f packaging/tauri/dedup_bundle_dylibs.py ]'
check "reproducible build pipeline script present" \
  '[ -x scripts/build-productive-desktop-app.sh ]'
check "Python 3.13 build environment" \
  '[ -x .venv-novtk-bundle/bin/python ] && .venv-novtk-bundle/bin/python -c "import sys; exit(0 if sys.version_info[:2] == (3, 13) else 1)"'
check "cadquery-ocp-novtk installed in the build environment (not cadquery-ocp)" \
  '.venv-novtk-bundle/bin/pip show cadquery-ocp-novtk >/dev/null 2>&1 && ! .venv-novtk-bundle/bin/pip show cadquery-ocp >/dev/null 2>&1'
check "legacy PySide6 app retained (not removed)" \
  '[ -d src/zerorodcad_desktop ]'
check "experiments/te002-tauri retained (not removed)" \
  '[ -d experiments/te002-tauri ]'

echo ""
echo "########################################################################"
echo "# BUILD-022 master gate: final release build inventory"
echo "########################################################################"

RELEASE_APP="desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
if [ -d "${RELEASE_APP}" ]; then
  "${PY}" - "${RELEASE_APP}" > "${REPORT_DIR}/final-inventory.json" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
total = files = dirs = links = 0
for p in root.rglob("*"):
    if p.is_symlink():
        links += 1
    elif p.is_file():
        files += 1
        total += p.stat().st_size
    elif p.is_dir():
        dirs += 1

result = {
    "bytes": total,
    "mib": round(total / 1024 / 1024, 2),
    "decimal_mb": round(total / 1000 / 1000, 2),
    "files": files,
    "dirs": dirs,
    "symlinks": links,
}
print(json.dumps(result, indent=2))
PY
  cat "${REPORT_DIR}/final-inventory.json"
else
  echo "SKIPPED: ${RELEASE_APP} not built. Run ./scripts/build-productive-desktop-app.sh release first."
  echo "(This does not fail the gate — M4's own script already validates a built bundle when present;"
  echo " this section is inventory-only.)"
fi

echo ""
echo "########################################################################"
echo "# BUILD-022 master gate: completion documentation present"
echo "########################################################################"
check "Build 022 completion record present" \
  '[ -f docs/migration/BUILD-022-COMPLETION.md ]'
check "Build 023 handoff present" \
  '[ -f docs/migration/BUILD-023-HANDOFF.md ]'

echo ""
echo "########################################################################"
if [ "${FAILED}" -eq 0 ]; then
  echo "BUILD-022 CONSISTENCY GATE: PASS"
  echo "########################################################################"
  exit 0
else
  echo "BUILD-022 CONSISTENCY GATE: FAIL — see above for the specific failing check(s)."
  echo "########################################################################"
  exit 1
fi
