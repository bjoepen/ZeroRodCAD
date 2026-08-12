#!/usr/bin/env bash
# Build 022 / Milestone 3 — Three.js Preview Foundation validation.
# Never touches experiments/te002-tauri or the legacy PySide6 app.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/build022-m3"
mkdir -p "${REPORT_DIR}"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python3.13"
fi

echo "== Build 022 M3: Frontend — vitest (mesh conversion, camera fit, preview state, status) =="
(cd desktop/frontend && npm run test)

echo "== Build 022 M3: Frontend — TypeScript =="
(cd desktop/frontend && npm run typecheck)

echo "== Build 022 M3: Frontend — production build =="
(cd desktop/frontend && npm run build)

echo "== Build 022 M3: Frontend — no external CDN references in our own source =="
# Only our own hand-written source/HTML — not dist/ or node_modules, whose
# minified/vendored content legitimately contains doc-comment URLs (e.g.
# Three.js shader citations) that are not network requests.
if grep -rniE "https?://" desktop/frontend/src desktop/frontend/index.html 2>/dev/null; then
  echo "external URL reference found in our own frontend source — must stay fully local" >&2
  exit 1
fi
echo "no external URLs in our own source"

echo "== Build 022 M3: Frontend — built HTML loads only local script/style tags =="
if grep -nE '<(script|link)[^>]+(src|href)="https?://' desktop/frontend/dist/index.html 2>/dev/null; then
  echo "built index.html references an external script/style — must stay fully local" >&2
  exit 1
fi
echo "built index.html references only local assets"

echo "== Build 022 M3: Rust — cargo test (sidecar lifecycle unchanged, app_info reports M3) =="
(cd desktop/src-tauri && cargo test)

echo "== Build 022 M3: Rust — cargo fmt --check =="
(cd desktop/src-tauri && cargo fmt --check)

echo "== Build 022 M3: Rust — cargo clippy -D warnings =="
(cd desktop/src-tauri && cargo clippy --all-targets -- -D warnings)

echo "== Build 022 M3: Rust — WebView capability still core:default only =="
if ! grep -q '"permissions": \["core:default"\]' desktop/src-tauri/capabilities/main-capability.json; then
  echo "main-capability.json no longer grants only core:default — security boundary regression" >&2
  exit 1
fi
echo "capability unchanged: core:default only"

echo "== Build 022 M3: Rust — CSP unchanged from M1/M2 baseline =="
EXPECTED_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost"
if ! grep -qF "${EXPECTED_CSP}" desktop/src-tauri/tauri.conf.json; then
  echo "CSP in tauri.conf.json no longer matches the M1/M2 restrictive baseline" >&2
  exit 1
fi
echo "CSP unchanged"

echo "== Build 022 M3: Python — sidecar tests unchanged (M3 did not touch the sidecar) =="
"${PY}" -m pytest \
  tests/test_zerorod_sidecar_protocol.py \
  tests/test_zerorod_sidecar_mesh_contract.py \
  tests/test_zerorod_sidecar_main.py \
  tests/test_zerorod_sidecar_persistent.py \
  -v

echo "== Build 022 M3: Python — No-VTK / No-PySide6 (real subprocess, TE-001.1-patched interpreter) =="
if [ -x ".venv-novtk-poc/bin/python" ]; then
  "${PY}" -m pytest tests/test_zerorod_sidecar_persistent.py::TestRealPersistentSubprocess -v
else
  echo "SKIPPED: .venv-novtk-poc not present; run scripts/validate-te001-novtk.sh first for this check"
fi

echo "== Build 022 M3: Integration — real preview request, mesh schema, no VTK in productive bundle =="
SIDECAR_BIN="desktop/sidecar-dist/zerorod-engine/zerorod-engine"
if [ -x "${SIDECAR_BIN}" ]; then
  printf '%s\n' \
    '{"schema":"zerorod-sidecar/v1","request_id":"1","command":"preview"}' \
    '{"schema":"zerorod-sidecar/v1","request_id":"2","command":"shutdown"}' \
    | "${SIDECAR_BIN}" --persistent > "${REPORT_DIR}/preview-integration.jsonl"
  "${PY}" - "${REPORT_DIR}/preview-integration.jsonl" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    responses = [json.loads(line) for line in f if line.strip()]
assert all(r["ok"] for r in responses), responses
result = responses[0]["result"]
assert result["schema"] == "zerorod-mesh/v1", result
names = sorted(m["name"] for m in result["meshes"])
assert names == ["body", "rod"], names
assert len(result["lines"]) > 0, "expected at least one line entry (virtual strings)"
print(f"preview integration: mesh schema correct, meshes={names}, lines={len(result['lines'])}")
PY
  if find "$(dirname "${SIDECAR_BIN}")" \( -iname "*vtk*" -o -iname "*pyside*" \) \
      | grep -v "cadquery_ocp_novtk" | grep -q .; then
    echo "VTK/PySide6-related file found in productive sidecar bundle" >&2
    exit 1
  fi
  echo "0 VTK/PySide6 files in productive sidecar bundle"
else
  echo "SKIPPED: ${SIDECAR_BIN} not built. Build it with:"
  echo "  .venv-novtk-bundle/bin/pyinstaller --noconfirm --clean --distpath desktop/sidecar-dist \\"
  echo "    --workpath build/zerorod-engine packaging/tauri/sidecar-onedir.spec"
fi

echo "== Build 022 M3: Frontend — real bundled-binary payload through the real mesh converter =="
if [ -x "${SIDECAR_BIN}" ]; then
  (cd desktop/frontend && npx vitest run src/mesh.realpayload.test.ts)
else
  echo "SKIPPED (same reason as above — real-payload test skips itself too when the binary is absent)"
fi

echo "== Build 022 M3: Repository — full regression suite =="
"${PY}" -m pytest -q

echo "== Build 022 M3: Repository — experiments/te002-tauri unchanged =="
if ! git diff --quiet -- experiments/te002-tauri/ 2>/dev/null; then
  echo "experiments/te002-tauri/ has uncommitted changes — must stay untouched" >&2
  git diff --stat -- experiments/te002-tauri/ >&2
  exit 1
fi
echo "experiments/te002-tauri/ unchanged"

echo "== Build 022 M3: Repository — legacy PySide6 app unchanged =="
if ! git diff --quiet -- src/zerorodcad_desktop/ 2>/dev/null; then
  echo "src/zerorodcad_desktop/ has uncommitted changes — must stay untouched" >&2
  git diff --stat -- src/zerorodcad_desktop/ >&2
  exit 1
fi
echo "src/zerorodcad_desktop/ unchanged"

echo "== Build 022 M3: Documentation present =="
for doc in \
  docs/migration/BUILD-022-M3-THREEJS-PREVIEW.md \
  docs/migration/BUILD-022-M3-HUMAN-VALIDATION.md
do
  if [ ! -f "${doc}" ]; then
    echo "missing required doc: ${doc}" >&2
    exit 1
  fi
done
echo "required Build 022 M3 docs present"

echo ""
echo "Build 022 Milestone 3 validation passed."
