#!/usr/bin/env bash
# Build 022 M4 — the reproducible productive packaging pipeline:
# sidecar (PyInstaller onedir, TE-002.2B baseline) -> stage into Tauri
# resources -> tauri build -> hash-gated dylib dedup (Optimization B,
# adapted productively). Never touches experiments/te002-tauri or the
# legacy PySide6 app.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script must run on macOS." >&2
  exit 1
fi

MODE="${1:-debug}"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"
SIDECAR_DIST="desktop/sidecar-dist"
RESOURCES_DIR="desktop/src-tauri/resources/zerorod-engine-onedir"
APP_PATH="desktop/src-tauri/target/${MODE}/bundle/macos/ZeroRodCAD.app"

if [[ ! -x "${BUNDLE_PYTHON}" ]]; then
  echo "${BUNDLE_VENV} not found. Run scripts/provision-novtk-bundle-venv.sh first" \
    "(it provisions the pinned, No-VTK-patched cadquery-ocp-novtk build environment" \
    "reproducibly from tracked repository state — see" \
    "docs/migration/BUILD-026-M1-PRODUCTION-BUNDLE-HARDENING.md)." >&2
  exit 1
fi

echo "== 1/4: building the productive onedir sidecar =="
rm -rf "${SIDECAR_DIST}" build/zerorod-engine
"${BUNDLE_VENV}/bin/pyinstaller" --noconfirm --clean --log-level WARN \
  --distpath "${SIDECAR_DIST}" --workpath build/zerorod-engine \
  packaging/tauri/sidecar-onedir.spec

echo "== 2/4: staging the sidecar into Tauri resources (preserving symlinks) =="
rm -rf "${RESOURCES_DIR}"
mkdir -p "$(dirname "${RESOURCES_DIR}")"
cp -R "${SIDECAR_DIST}/zerorod-engine" "${RESOURCES_DIR}"

echo "== 3/4: building the Tauri app (${MODE}) =="
rm -rf "desktop/src-tauri/target/${MODE}/bundle"
(
  cd desktop/src-tauri
  if [[ "${MODE}" == "release" ]]; then
    ../frontend/node_modules/.bin/tauri build
  else
    ../frontend/node_modules/.bin/tauri build --debug
  fi
)

echo "== 4/4: hash-gated dylib dedup (restores Tauri's dereferenced symlinks) =="
if [[ -x ".venv/bin/python" ]]; then
  DEDUP_PYTHON=".venv/bin/python"
else
  DEDUP_PYTHON="python3.13"
fi
"${DEDUP_PYTHON}" packaging/tauri/dedup_bundle_dylibs.py \
  "${SIDECAR_DIST}/zerorod-engine/_internal" \
  "${APP_PATH}/Contents/Resources/zerorod-engine-onedir/_internal"

echo ""
echo "Productive app built at: ${APP_PATH}"
du -sh "${APP_PATH}"
