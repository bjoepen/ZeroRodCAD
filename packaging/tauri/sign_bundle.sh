#!/usr/bin/env bash
# Build 026 Finalization — signing INFRASTRUCTURE, not real signing.
#
# Signs every nested Mach-O component of the productive ZeroRodCAD.app in
# the correct order (nested dylibs/extensions -> sidecar executable -> main
# executable -> outer bundle), then the bundle itself — never a single
# `codesign --deep` pass, per docs/migration/BUILD-026-SIGNING-NOTARIZATION-ANALYSIS.md's
# explicit recommendation (a single --deep pass signs nested code with the
# outer bundle's own flags/entitlements in one step, which is adequate for
# many apps but not auditable/reproducible in the way this script is).
#
# This script requires a real Developer ID Application signing identity to
# do anything destructive. It is intended to be run with --dry-run (the
# default, safe mode) for structural verification without any credential;
# real signing requires an explicit --identity argument naming a certificate
# that must already exist in the local Keychain — nothing here creates,
# imports, or exports a certificate, and no credential is read, printed, or
# requested by this script.
#
# Usage:
#   packaging/tauri/sign_bundle.sh <path-to-.app> [--identity "Developer ID Application: ..."] [--dry-run]
#
# With no --identity, or with --dry-run, this script only PRINTS the exact
# codesign invocations it would run, in order, and verifies the bundle
# structure — it performs no signing.
set -euo pipefail

APP_PATH="${1:?usage: sign_bundle.sh <path-to-.app> [--identity \"Developer ID Application: ...\"] [--dry-run]}"
shift || true

IDENTITY=""
DRY_RUN=1
while [ $# -gt 0 ]; do
  case "$1" in
    --identity)
      IDENTITY="$2"
      DRY_RUN=0
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ ! -d "${APP_PATH}" ]; then
  echo "not a directory: ${APP_PATH}" >&2
  exit 1
fi

MAIN_EXECUTABLE="${APP_PATH}/Contents/MacOS/zerorod-desktop"
SIDECAR_EXECUTABLE="${APP_PATH}/Contents/Resources/zerorod-engine-onedir/zerorod-engine"
ENTITLEMENTS=""
# Per docs/migration/BUILD-026-SIGNING-NOTARIZATION-ANALYSIS.md's evidence-based
# conclusion: no entitlement is currently known to be required (no JIT
# dependency in the shipped bundle — numba/llvmlite excluded; no elevated
# resource access anywhere in the WebView-facing capability set). If a real
# signed/hardened-runtime build later demonstrates a genuine load failure,
# add the specific entitlement then, evidence-based — not speculatively
# here. ENTITLEMENTS stays empty; --entitlements is omitted from every
# codesign invocation below rather than pointing at a fabricated file.

if [ ! -x "${MAIN_EXECUTABLE}" ]; then
  echo "main executable not found: ${MAIN_EXECUTABLE}" >&2
  exit 1
fi
if [ ! -x "${SIDECAR_EXECUTABLE}" ]; then
  echo "sidecar executable not found: ${SIDECAR_EXECUTABLE}" >&2
  exit 1
fi

echo "== sign_bundle: discovering nested Mach-O components (excluding main/sidecar executables and the outer bundle) =="
NESTED_FILES=()
while IFS= read -r -d '' f; do
  if [ "${f}" = "${MAIN_EXECUTABLE}" ] || [ "${f}" = "${SIDECAR_EXECUTABLE}" ]; then
    continue
  fi
  if [ -L "${f}" ]; then
    continue
  fi
  if file "${f}" 2>/dev/null | grep -q "Mach-O"; then
    NESTED_FILES+=("${f}")
  fi
done < <(find "${APP_PATH}" -type f -print0)

echo "  found ${#NESTED_FILES[@]} nested Mach-O components to sign before the executables"

sign_one() {
  local target="$1"
  local cmd=(codesign --force --sign "${IDENTITY}" --options runtime --timestamp)
  if [ -n "${ENTITLEMENTS}" ]; then
    cmd+=(--entitlements "${ENTITLEMENTS}")
  fi
  cmd+=("${target}")
  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "  [dry-run] ${cmd[*]}"
  else
    echo "  signing ${target}"
    "${cmd[@]}"
  fi
}

echo "== sign_bundle: step 1/4 — nested dylibs/extensions =="
for f in "${NESTED_FILES[@]}"; do
  sign_one "${f}"
done

echo "== sign_bundle: step 2/4 — sidecar executable =="
sign_one "${SIDECAR_EXECUTABLE}"

echo "== sign_bundle: step 3/4 — main executable =="
sign_one "${MAIN_EXECUTABLE}"

echo "== sign_bundle: step 4/4 — outer .app bundle (sealed last, after every nested component) =="
sign_one "${APP_PATH}"

if [ "${DRY_RUN}" -eq 1 ]; then
  echo ""
  echo "== sign_bundle: DRY RUN — no signing performed. Re-run with --identity \"Developer ID Application: <Org> (<TEAMID>)\" to sign for real (requires that certificate to already exist in the local Keychain). =="
else
  echo ""
  echo "== sign_bundle: verifying the signed bundle =="
  codesign --verify --deep --strict --verbose=2 "${APP_PATH}"
  spctl -a -vv "${APP_PATH}" || true
  echo "== sign_bundle: PASS =="
fi
