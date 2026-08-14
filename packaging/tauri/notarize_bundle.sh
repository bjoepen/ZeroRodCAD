#!/usr/bin/env bash
# Build 026 Finalization — notarization INFRASTRUCTURE, not real notarization.
#
# Documents and scripts the modern (notarytool-based) submission workflow
# for a signed DMG/ZIP, per
# docs/migration/BUILD-026-SIGNING-NOTARIZATION-ANALYSIS.md. This script
# requires a real Apple ID + app-specific password (or App Store Connect API
# key) via a `notarytool`-managed Keychain profile to do anything real — it
# never accepts, reads, prints, or requests a credential directly. With no
# --profile argument, it only prints the exact commands it would run.
#
# One-time setup this script does NOT perform (must be done manually,
# interactively, by whoever holds real credentials):
#   xcrun notarytool store-credentials "<profile-name>" \
#     --apple-id "<apple-id>" --team-id "<TEAMID>" --password "<app-specific-password>"
# (stores the credential in the LOCAL machine's Keychain, referenced only by
# profile name thereafter — never as a literal argument this script passes)
#
# Usage:
#   packaging/tauri/notarize_bundle.sh <path-to.dmg> [--profile <keychain-profile-name>]
set -euo pipefail

ARTIFACT_PATH="${1:?usage: notarize_bundle.sh <path-to.dmg-or-.zip> [--profile <keychain-profile-name>]}"
shift || true

PROFILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ ! -f "${ARTIFACT_PATH}" ]; then
  echo "not a file: ${ARTIFACT_PATH}" >&2
  exit 1
fi

echo "== notarize_bundle: target artifact: ${ARTIFACT_PATH} =="

if [ -z "${PROFILE}" ]; then
  echo ""
  echo "== notarize_bundle: DRY RUN — no --profile given, no submission will be made =="
  echo "  Would run:"
  echo "    xcrun notarytool submit \"${ARTIFACT_PATH}\" --keychain-profile \"<profile-name>\" --wait"
  echo "  On success, would then run:"
  echo "    xcrun stapler staple \"${ARTIFACT_PATH}\""
  echo "    xcrun stapler validate \"${ARTIFACT_PATH}\""
  echo "    spctl -a -vv --type execute \"${ARTIFACT_PATH}\""
  echo ""
  echo "  Real submission requires a Keychain profile created once, interactively, via:"
  echo "    xcrun notarytool store-credentials \"<profile-name>\" --apple-id \"<id>\" --team-id \"<TEAMID>\" --password \"<app-specific-password>\""
  echo "  (never run by this script, never scripted with a literal credential)."
  exit 0
fi

echo "== notarize_bundle: submitting via keychain profile '${PROFILE}' =="
SUBMIT_OUTPUT="$(xcrun notarytool submit "${ARTIFACT_PATH}" --keychain-profile "${PROFILE}" --wait 2>&1)"
echo "${SUBMIT_OUTPUT}"

if ! echo "${SUBMIT_OUTPUT}" | grep -q "status: Accepted"; then
  echo "notarization was not accepted — see output above (and 'xcrun notarytool log <submission-id> --keychain-profile ${PROFILE}' for detail)" >&2
  exit 1
fi

echo "== notarize_bundle: stapling =="
xcrun stapler staple "${ARTIFACT_PATH}"

echo "== notarize_bundle: validating =="
xcrun stapler validate "${ARTIFACT_PATH}"
spctl -a -vv --type execute "${ARTIFACT_PATH}" || true

echo "== notarize_bundle: PASS =="
