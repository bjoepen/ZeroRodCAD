#!/usr/bin/env bash
# Build 022 / Milestone 2 — Productive Sidecar & Rust Lifecycle validation.
# Never touches experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build022-m2"
mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3.13"
fi

echo "== Build 022 M2: Python — sidecar unit/protocol/contract tests =="
"${PY}" -m pytest \
  tests/test_zerorod_sidecar_protocol.py \
  tests/test_zerorod_sidecar_mesh_contract.py \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  -v

echo "== Build 022 M2: Python — ruff (sidecar package + its tests) =="
"${PY}" -m ruff check src/zerorod_sidecar tests/test_zerorod_sidecar_*.py
"${PY}" -m ruff format --check src/zerorod_sidecar tests/test_zerorod_sidecar_*.py

echo "== Build 022 M2: Python — No-VTK / No-PySide6 (real subprocess, TE-001.1-patched interpreter) =="
if [ -x ".venv-novtk-poc/bin/python" ]; then
  "${PY}" -m pytest tests/test_zerorod_sidecar_persistent.py::TestRealPersistentSubprocess -v
else
  echo "SKIPPED: .venv-novtk-poc not present; run scripts/validate-te001-novtk.sh first for this check"
fi

echo "== Build 022 M2: Rust — cargo test =="
(cd desktop/src-tauri && cargo test)

echo "== Build 022 M2: Rust — cargo fmt --check =="
(cd desktop/src-tauri && cargo fmt --check)

echo "== Build 022 M2: Rust — cargo clippy -D warnings =="
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)

echo "== Build 022 M2: Frontend — vitest =="
(cd desktop/frontend && npm run test)

echo "== Build 022 M2: Frontend — TypeScript =="
(cd desktop/frontend && npm run typecheck)

echo "== Build 022 M2: Frontend — production build =="
(cd desktop/frontend && npm run build)

echo "== Build 022 M2: Integration — productive onedir sidecar, real protocol round trip =="
SIDECAR_BIN="desktop/sidecar-dist/zerorod-engine/zerorod-engine"
if [ -x "${SIDECAR_BIN}" ]; then
  printf '%s\n' \
    '{"schema":"zerorod-sidecar/v1","request_id":"1","command":"ping"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"2","command":"status"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"3","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"4","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"5","command":"shutdown"}' \
    | "${SIDECAR_BIN}" --persistent > "${REPORT_DIR}/sidecar-integration.jsonl"
  LINES=$(wc -l < "${REPORT_DIR}/sidecar-integration.jsonl" | tr -d ' ')
  if [ "${LINES}" != "5" ]; then
    echo "expected 5 response lines, got ${LINES}" >&2
    exit 1
  fi
  "${PY}" - "${REPORT_DIR}/sidecar-integration.jsonl" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    responses = [json.loads(line) for line in f if line.strip()]
assert all(r["ok"] for r in responses), responses
assert responses[1]["result"]["vtk_installed"] is False, responses[1]
assert responses[2]["result"]["schema"] == "zerorod-mesh/v1"
print("sidecar integration: 5/5 ok, vtk_installed=False, mesh schema correct")
PY
  echo "== Build 022 M2: Integration — 0 orphan processes after the subprocess above exited =="
  if pgrep -f "desktop/sidecar-dist/zerorod-engine/zerorod-engine" >/dev/null 2>&1; then
    echo "orphan zerorod-engine process(es) found after integration test" >&2
    pgrep -fl "desktop/sidecar-dist/zerorod-engine/zerorod-engine" >&2
    exit 1
  fi
  echo "0 orphan processes"
else
  echo "SKIPPED: ${SIDECAR_BIN} not built. Build it with:"
  echo "  .venv-novtk-bundle/bin/pyinstaller --noconfirm --clean --distpath desktop/sidecar-dist \\"
  echo "    --workpath build/zerorod-engine packaging/tauri/sidecar-onedir.spec"
fi

echo "== Build 022 M2: Repository — full regression suite =="
"${PY}" -m pytest -q

echo "== Build 022 M2: Repository — experiments/te002-tauri unchanged =="
if ! git diff --quiet -- experiments/te002-tauri/ 2>/dev/null; then
  echo "experiments/te002-tauri/ has uncommitted changes — must stay untouched" >&2
  git diff --stat -- experiments/te002-tauri/ >&2
  exit 1
fi
echo "experiments/te002-tauri/ unchanged"

echo "== Build 022 M2: Repository — legacy PySide6 app unchanged =="
if ! git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null; then
  echo "src/zerorodcad_desktop/ has uncommitted changes — must stay untouched" >&2
  git diff --stat -- src/zerorodcad_desktop/ >&2
  exit 1
fi
echo "src/zerorodcad_desktop/ unchanged"

echo "== Build 022 M2: Documentation present =="
for doc in \
  docs/migration/BUILD-022-M2-SIDECAR-LIFECYCLE.md \
  docs/migration/BUILD-022-M2-HUMAN-VALIDATION.md
do
  if [ ! -f "${doc}" ]; then
    echo "missing required doc: ${doc}" >&2
    exit 1
  fi
done
echo "required Build 022 M2 docs present"

echo ""
echo "Build 022 Milestone 2 validation passed."
