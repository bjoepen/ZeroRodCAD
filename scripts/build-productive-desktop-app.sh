#!/usr/bin/env bash
# Build 022 M4 — the reproducible productive packaging pipeline:
# sidecar (PyInstaller onedir, TE-002.2B baseline) -> stage into Tauri
# resources -> tauri build -> hash-gated dylib dedup (Optimization B,
# adapted productively) -> DMG (Build 026 Finalization). Never touches
# experiments/te002-tauri or the legacy PySide6 app.
#
# Build 026 Finalization: the Tauri build step explicitly requests only the
# "app" bundle target (`--bundles app`), even though tauri.conf.json's own
# `bundle.targets` also lists "dmg" (documenting the app's supported
# distribution formats) — Tauri's native DMG bundling runs BEFORE the dylib
# dedup step in a single `tauri build` invocation, which would ship ~112 MiB
# of avoidable duplicate dylibs (Tauri's resource-copy step dereferences
# PyInstaller's own symlinks; the dedup step restores them, but only after
# the app is bundled). The DMG is instead built as an explicit final step
# (5/5), from the already-deduped .app, so the shipped DMG reflects the
# smaller, deduplicated bundle.
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

echo "== 3/5: building the Tauri app (${MODE}, app bundle only — dmg comes after dedup) =="
rm -rf "desktop/src-tauri/target/${MODE}/bundle"
(
  cd desktop/src-tauri
  if [[ "${MODE}" == "release" ]]; then
    ../frontend/node_modules/.bin/tauri build --bundles app
  else
    ../frontend/node_modules/.bin/tauri build --debug --bundles app
  fi
)

echo "== 4/5: hash-gated dylib dedup (restores Tauri's dereferenced symlinks) =="
if [[ -x ".venv/bin/python" ]]; then
  DEDUP_PYTHON=".venv/bin/python"
else
  DEDUP_PYTHON="python3.13"
fi
"${DEDUP_PYTHON}" packaging/tauri/dedup_bundle_dylibs.py \
  "${SIDECAR_DIST}/zerorod-engine/_internal" \
  "${APP_PATH}/Contents/Resources/zerorod-engine-onedir/_internal"

echo "== 5/5: building the DMG from the deduplicated .app =="
DMG_DIR="desktop/src-tauri/target/${MODE}/bundle/dmg"
DMG_STAGING="desktop/src-tauri/target/${MODE}/bundle/dmg-staging"
DMG_PATH="${DMG_DIR}/ZeroRodCAD.dmg"
rm -rf "${DMG_DIR}" "${DMG_STAGING}"
mkdir -p "${DMG_DIR}" "${DMG_STAGING}"
ditto "${APP_PATH}" "${DMG_STAGING}/ZeroRodCAD.app"
ln -s /Applications "${DMG_STAGING}/Applications"
hdiutil create -volname "ZeroRodCAD" -srcfolder "${DMG_STAGING}" -ov -format UDZO "${DMG_PATH}" >/dev/null
rm -rf "${DMG_STAGING}"

echo ""
echo "Productive app built at: ${APP_PATH}"
du -sh "${APP_PATH}"
echo "DMG built at: ${DMG_PATH}"
du -sh "${DMG_PATH}"
