#!/usr/bin/env bash
# Build 022 / Milestone 4 — Productive Packaging Baseline validation.
# Never touches experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build022-m4"
mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3.13"
fi

echo "== Build 022 M4: Packaging config — onedir only, no onefile fallback =="
if grep -q "externalBin" desktop/src-tauri/tauri.conf.json; then
  echo "externalBin found in tauri.conf.json — onefile fallback must not be bundled productively" >&2
  exit 1
fi
echo "no externalBin key — onedir is the only shipped sidecar strategy"

echo "== Build 022 M4: Packaging config — numba/llvmlite/scipy excluded =="
for dep in numba llvmlite scipy; do
  if ! grep -q "\"${dep}\"" packaging/tauri/sidecar-onedir.spec; then
    echo "\"${dep}\" not found in packaging/tauri/sidecar-onedir.spec excludes" >&2
    exit 1
  fi
done
echo "numba, llvmlite, scipy all present in the spec's excludes list"

echo "== Build 022 M4: Python — dedup script tests (ruff + import sanity) =="
"${PY}" -m ruff check packaging/tauri/dedup_bundle_dylibs.py
"${PY}" -m ruff format --check packaging/tauri/dedup_bundle_dylibs.py
"${PY}" -c "import ast; ast.parse(open('packaging/tauri/dedup_bundle_dylibs.py').read())"
echo "dedup_bundle_dylibs.py: ruff clean, parses correctly"

SIDECAR_PRISTINE="desktop/sidecar-dist/zerorod-engine"
RELEASE_APP="desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
DEBUG_APP="desktop/src-tauri/target/debug/bundle/macos/ZeroRodCAD.app"
if [ -d "${RELEASE_APP}" ]; then
  APP="${RELEASE_APP}"
elif [ -d "${DEBUG_APP}" ]; then
  APP="${DEBUG_APP}"
else
  APP=""
fi

if [ -n "${APP}" ] && [ -d "${SIDECAR_PRISTINE}" ]; then
  TARGET_INTERNAL="${APP}/Contents/Resources/zerorod-engine-onedir/_internal"

  echo "== Build 022 M4: Dedup — no VTK/PySide6/Qt/numba/llvmlite/scipy in final bundle =="
  for pat in "*vtk*" "*pyside*" "*[Qq]t*" "*numba*" "*llvmlite*" "*scipy*"; do
    matches=$(find "${APP}" -iname "${pat}" 2>/dev/null | grep -v "cadquery_ocp_novtk" || true)
    if [ -n "${matches}" ]; then
      echo "unexpected match for '${pat}': ${matches}" >&2
      exit 1
    fi
  done
  echo "0 VTK/PySide6/Qt/numba/llvmlite/scipy files in ${APP}"

  echo "== Build 022 M4: Dedup — symlink safety (relative, resolves inside bundle, no broken links) =="
  "${PY}" - "${APP}" <<'PY'
import os
import sys
from pathlib import Path

app = Path(sys.argv[1]).resolve()
bad = []
count = 0
for p in app.rglob("*"):
    if not p.is_symlink():
        continue
    count += 1
    target = os.readlink(p)
    if os.path.isabs(target):
        bad.append(f"{p}: absolute symlink target {target!r}")
        continue
    resolved = (p.parent / target).resolve()
    try:
        resolved.relative_to(app)
    except ValueError:
        bad.append(f"{p}: resolves outside the bundle: {resolved}")
        continue
    if not resolved.exists():
        bad.append(f"{p}: broken symlink, target does not exist: {resolved}")

if bad:
    print(f"{len(bad)} unsafe/broken symlink(s) found:", file=sys.stderr)
    for b in bad:
        print(f"  {b}", file=sys.stderr)
    sys.exit(1)
print(f"{count} symlinks checked, all relative/safe/resolve inside the bundle")
PY

  echo "== Build 022 M4: Dedup — idempotency (second run against the built app is a no-op) =="
  "${PY}" packaging/tauri/dedup_bundle_dylibs.py --json \
    "${SIDECAR_PRISTINE}/_internal" "${TARGET_INTERNAL}" > "${REPORT_DIR}/dedup-idempotency-check.json"
  RELINKED=$("${PY}" -c "import json; print(json.load(open('${REPORT_DIR}/dedup-idempotency-check.json'))['relinked_count'])")
  if [ "${RELINKED}" != "0" ]; then
    echo "expected 0 newly-relinked files on a second dedup pass (bundle should already be deduped), got ${RELINKED}" >&2
    exit 1
  fi
  echo "second dedup pass relinked 0 files — idempotent"

  echo "== Build 022 M4: Integration — exact bundled sidecar (ping/status/preview/repeated/error/shutdown) =="
  BUNDLED_SIDECAR="${APP}/Contents/Resources/zerorod-engine-onedir/zerorod-engine"
  printf '%s\n' \
    '{"schema":"zerorod-sidecar/v1","request_id":"1","command":"ping"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"2","command":"status"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"3","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"4","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"5","command":"unknown-command"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"6","command":"shutdown"}' \
    | "${BUNDLED_SIDECAR}" --persistent > "${REPORT_DIR}/final-bundle-integration.jsonl"
  "${PY}" - "${REPORT_DIR}/final-bundle-integration.jsonl" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    responses = [json.loads(line) for line in f if line.strip()]
assert len(responses) == 6, responses
assert responses[0]["ok"] and responses[0]["result"]["status"] == "ok"
assert responses[1]["ok"] and responses[1]["result"]["vtk_installed"] is False
assert responses[2]["ok"] and responses[2]["result"]["schema"] == "zerorod-mesh/v1"
assert responses[3]["ok"]
assert not responses[4]["ok"] and responses[4]["error"]["code"] == "unknown_command"
assert responses[5]["ok"] and responses[5]["result"]["status"] == "shutting_down"
print("final bundle integration: ping/status/preview x2/error-path/shutdown all correct")
PY

  echo "== Build 022 M4: Integration — 0 orphan processes after the subprocess above exited =="
  if pgrep -f "zerorod-engine-onedir/zerorod-engine" >/dev/null 2>&1; then
    echo "orphan zerorod-engine process(es) found" >&2
    pgrep -fl "zerorod-engine-onedir/zerorod-engine" >&2
    exit 1
  fi
  echo "0 orphan processes"
else
  echo "SKIPPED (dedup/integration/symlink checks): no built app and/or pristine sidecar found."
  echo "Run scripts/build-productive-desktop-app.sh [debug|release] first."
fi

echo "== Build 022 M4: Rust — cargo test / fmt / clippy =="
(cd desktop/src-tauri && cargo test)
(cd desktop/src-tauri && cargo fmt --check)
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)

echo "== Build 022 M4: Rust — WebView capability and CSP unchanged =="
if ! grep -q '"permissions": \["core:default"\]' desktop/src-tauri/capabilities/main-capability.json; then
  echo "main-capability.json no longer grants only core:default — security boundary regression" >&2
  exit 1
fi
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
if ! grep -qF "${EXPECTED_CSP}" desktop/src-tauri/tauri.conf.json; then
  echo "CSP no longer matches the M1-M3 restrictive baseline" >&2
  exit 1
fi
echo "capability and CSP unchanged"

echo "== Build 022 M4: Frontend — vitest / TypeScript / build =="
(cd desktop/frontend && npm run test)
(cd desktop/frontend && npm run typecheck)
(cd desktop/frontend && npm run build)

echo "== Build 022 M4: Python — sidecar tests (unchanged) =="
"${PY}" -m pytest \
  tests/test_zerorod_sidecar_protocol.py \
  tests/test_zerorod_sidecar_mesh_contract.py \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  -v

echo "== Build 022 M4: Python — No-VTK / No-PySide6 (real subprocess, TE-001.1-patched interpreter) =="
if [ -x ".venv-novtk-poc/bin/python" ]; then
  "${PY}" -m pytest tests/test_zerorod_sidecar_persistent.py::TestRealPersistentSubprocess -v
else
  echo "SKIPPED: .venv-novtk-poc not present"
fi

echo "== Build 022 M4: Repository — full regression suite =="
"${PY}" -m pytest -q

echo "== Build 022 M4: Repository — experiments/te002-tauri unchanged =="
if ! git diff --quiet -- experiments/te002-tauri/ 2>/dev/null; then
  echo "experiments/te002-tauri/ has uncommitted changes — must stay untouched" >&2
  git diff --stat -- experiments/te002-tauri/ >&2
  exit 1
fi
echo "experiments/te002-tauri/ unchanged"

echo "== Build 022 M4: Repository — legacy PySide6 app unchanged =="
if ! git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null; then
  echo "src/zerorodcad_desktop/ has uncommitted changes — must stay untouched" >&2
  git diff --stat -- src/zerorodcad_desktop/ >&2
  exit 1
fi
echo "src/zerorodcad_desktop/ unchanged"

echo "== Build 022 M4: Documentation present =="
for doc in \
  docs/migration/BUILD-022-M4-PRODUCTIVE-PACKAGING.md \
  docs/migration/BUILD-022-M4-HUMAN-VALIDATION.md
do
  if [ ! -f "${doc}" ]; then
    echo "missing required doc: ${doc}" >&2
    exit 1
  fi
done
echo "required Build 022 M4 docs present"

echo ""
echo "Build 022 Milestone 4 validation passed."
