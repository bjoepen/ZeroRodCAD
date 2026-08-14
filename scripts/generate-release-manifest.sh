#!/usr/bin/env bash
# Build 026 Finalization — generates a flat, secret-free release manifest
# and SHA-256 checksums for the final unsigned Release Candidate artifacts.
#
# Usage: scripts/generate-release-manifest.sh <path-to-.app> <path-to-.dmg> <output-dir>
set -euo pipefail

cd "$(dirname "$0")/.."

APP_PATH="${1:?usage: generate-release-manifest.sh <path-to-.app> <path-to-.dmg> <output-dir>}"
DMG_PATH="${2:?usage: generate-release-manifest.sh <path-to-.app> <path-to-.dmg> <output-dir>}"
OUTPUT_DIR="${3:?usage: generate-release-manifest.sh <path-to-.app> <path-to-.dmg> <output-dir>}"

mkdir -p "${OUTPUT_DIR}"

echo "== generate-release-manifest: computing unsigned .app fingerprint =="
# Same methodology as Build 025's own deterministic bundle fingerprint:
# sorted relative paths, per-file SHA-256, symlink targets, aggregate SHA-256.
FINGERPRINT_TMP="$(mktemp)"
(
  cd "${APP_PATH}"
  find . -type f -print0 | sort -z | while IFS= read -r -d '' f; do
    h=$(shasum -a 256 "$f" | awk '{print $1}')
    printf '%s  %s\n' "$h" "${f#./}"
  done
  find . -type l -print0 | sort -z | while IFS= read -r -d '' f; do
    t=$(readlink "$f")
    printf 'SYMLINK %s -> %s\n' "${f#./}" "$t"
  done
) | sort > "${FINGERPRINT_TMP}"
APP_FINGERPRINT="$(shasum -a 256 "${FINGERPRINT_TMP}" | awk '{print $1}')"
rm -f "${FINGERPRINT_TMP}"
echo "  ${APP_FINGERPRINT}"

echo "== generate-release-manifest: DMG SHA-256 =="
DMG_SHA256="$(shasum -a 256 "${DMG_PATH}" | awk '{print $1}')"
echo "  ${DMG_SHA256}"

GIT_COMMIT="$(git rev-parse HEAD)"
FRONTEND_ASSET="$(find desktop/frontend/dist/assets -name "index-*.js" | head -1)"
FRONTEND_ASSET_SHA256=""
if [ -n "${FRONTEND_ASSET}" ]; then
  FRONTEND_ASSET_SHA256="$(shasum -a 256 "${FRONTEND_ASSET}" | awk '{print $1}')"
fi

MANIFEST_PATH="${OUTPUT_DIR}/release-manifest.json"
cat > "${MANIFEST_PATH}" <<JSON
{
  "product": "ZeroRodCAD",
  "public_version": "0.1.0",
  "engineering_build": "026 / Final",
  "git_commit": "${GIT_COMMIT}",
  "architecture": "arm64",
  "bundle_identifier": "de.zerorodcad.desktop",
  "minimum_macos": "11.1",
  "frontend_asset": "$(basename "${FRONTEND_ASSET}")",
  "frontend_asset_sha256": "${FRONTEND_ASSET_SHA256}",
  "unsigned_app_fingerprint_sha256": "${APP_FINGERPRINT}",
  "dmg_filename": "$(basename "${DMG_PATH}")",
  "dmg_sha256": "${DMG_SHA256}",
  "signed": false,
  "notarized": false,
  "signing_identity": null,
  "notarization_status": null
}
JSON

echo "== generate-release-manifest: checksums file =="
CHECKSUMS_PATH="${OUTPUT_DIR}/SHA256SUMS.txt"
{
  echo "${APP_FINGERPRINT}  $(basename "${APP_PATH}") (unsigned .app content fingerprint, not a file hash)"
  echo "${DMG_SHA256}  $(basename "${DMG_PATH}")"
} > "${CHECKSUMS_PATH}"

echo ""
echo "Manifest:   ${MANIFEST_PATH}"
echo "Checksums:  ${CHECKSUMS_PATH}"
cat "${MANIFEST_PATH}"
