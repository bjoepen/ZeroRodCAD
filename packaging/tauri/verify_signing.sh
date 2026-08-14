#!/usr/bin/env bash
# Build 026 Finalization — read-only signing/notarization state verification.
# No credentials, no signing, no notarization performed. Safe to run against
# an ad-hoc/unsigned bundle (reports that honestly) or a really-signed one.
#
# Usage: packaging/tauri/verify_signing.sh <path-to-.app-or-.dmg>
set -euo pipefail

TARGET="${1:?usage: verify_signing.sh <path-to-.app-or-.dmg>}"

if [ ! -e "${TARGET}" ]; then
  echo "not found: ${TARGET}" >&2
  exit 1
fi

echo "== verify_signing: codesign -dv --verbose=4 =="
codesign -dv --verbose=4 "${TARGET}" 2>&1 || true

echo ""
echo "== verify_signing: codesign --verify --deep --strict =="
codesign --verify --deep --strict --verbose=2 "${TARGET}" 2>&1 || echo "  (verification failed or bundle is not signed with a real identity — expected for an ad-hoc/unsigned bundle)"

echo ""
echo "== verify_signing: spctl -a -vv =="
spctl -a -vv "${TARGET}" 2>&1 || echo "  (Gatekeeper assessment failed — expected for an ad-hoc/unsigned bundle)"

echo ""
echo "== verify_signing: entitlements =="
codesign -d --entitlements :- "${TARGET}" 2>&1 || echo "  (no entitlements embedded)"

echo ""
echo "== verify_signing: quarantine attribute =="
xattr -l "${TARGET}" 2>&1 | grep -i quarantine || echo "  (no com.apple.quarantine attribute — expected for a locally-built, never-downloaded artifact)"

echo ""
echo "== verify_signing: done (read-only, no credentials used) =="
