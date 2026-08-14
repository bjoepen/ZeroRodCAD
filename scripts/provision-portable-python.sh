#!/usr/bin/env bash
# Build 026 Finalization — reproducible, pinned, portable CPython 3.13
# provisioning for the productive Tauri packaging environment.
#
# Replaces the previous dependency on whatever `python3.13` a developer's
# machine happened to have on PATH (Homebrew's bottle, which floats its own
# MACOSX_DEPLOYMENT_TARGET to match the build machine's current OS — the
# root cause of Build 026 M1's honest-but-inflated 26.0 floor finding).
# Source: astral-sh/python-build-standalone (the same portable-Python build
# infrastructure `uv`/`rye`/`pdm` rely on), proven in
# docs/migration/BUILD-026-M11-PORTABLE-PYTHON-EVALUATION.md to produce a
# full productive bundle with a real, measured Mach-O floor of 11.1.
#
# Usage: scripts/provision-portable-python.sh [install-dir]
#   install-dir defaults to .portable-python-3.13
set -euo pipefail

cd "$(dirname "$0")/.."

RELEASE_TAG="20260807"
ASSET_NAME="cpython-3.13.15+20260807-aarch64-apple-darwin-install_only.tar.gz"
ASSET_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${RELEASE_TAG}/${ASSET_NAME}"
EXPECTED_SHA256="ebcf53fe921c356ad2eecfcea370cb744e7bd96fdef41a53e1e8f32a15c6dfeb"
EXPECTED_PYTHON_VERSION="3.13.15"

INSTALL_DIR="${1:-.portable-python-3.13}"
DOWNLOAD_DIR="build/downloads"
ARCHIVE_PATH="${DOWNLOAD_DIR}/${ASSET_NAME}"

if [ -x "${INSTALL_DIR}/python/bin/python3.13" ]; then
  ACTUAL_VERSION="$("${INSTALL_DIR}/python/bin/python3.13" --version 2>&1 | awk '{print $2}')"
  if [ "${ACTUAL_VERSION}" = "${EXPECTED_PYTHON_VERSION}" ]; then
    echo "== provision-portable-python: ${INSTALL_DIR} already provisioned (Python ${ACTUAL_VERSION}) — idempotent no-op =="
    exit 0
  else
    echo "${INSTALL_DIR} exists but reports Python ${ACTUAL_VERSION}, expected ${EXPECTED_PYTHON_VERSION} — removing and re-provisioning" >&2
    rm -rf "${INSTALL_DIR}"
  fi
fi

echo "== provision-portable-python: downloading ${ASSET_NAME} =="
mkdir -p "${DOWNLOAD_DIR}"
if [ ! -f "${ARCHIVE_PATH}" ] || [ "$(shasum -a 256 "${ARCHIVE_PATH}" | awk '{print $1}')" != "${EXPECTED_SHA256}" ]; then
  curl -fL --retry 3 -o "${ARCHIVE_PATH}" "${ASSET_URL}"
fi

echo "== provision-portable-python: verifying SHA-256 =="
ACTUAL_SHA256="$(shasum -a 256 "${ARCHIVE_PATH}" | awk '{print $1}')"
if [ "${ACTUAL_SHA256}" != "${EXPECTED_SHA256}" ]; then
  echo "CHECKSUM MISMATCH for ${ASSET_NAME}" >&2
  echo "  expected: ${EXPECTED_SHA256}" >&2
  echo "  actual:   ${ACTUAL_SHA256}" >&2
  echo "Refusing to use a downloaded artifact that does not match the pinned checksum." >&2
  rm -f "${ARCHIVE_PATH}"
  exit 1
fi
echo "  OK   ${ACTUAL_SHA256}"

echo "== provision-portable-python: verifying archive layout =="
if ! tar tzf "${ARCHIVE_PATH}" | grep -q "^python/bin/python3.13$"; then
  echo "unexpected archive layout: python/bin/python3.13 not found in ${ARCHIVE_PATH}" >&2
  exit 1
fi
if ! tar tzf "${ARCHIVE_PATH}" | grep -q "^python/lib/python3.13/os.py$"; then
  echo "unexpected archive layout: python/lib/python3.13/os.py not found in ${ARCHIVE_PATH}" >&2
  exit 1
fi
echo "  OK   layout matches expected python-build-standalone install_only shape"

echo "== provision-portable-python: extracting to ${INSTALL_DIR} =="
rm -rf "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
tar xzf "${ARCHIVE_PATH}" -C "${INSTALL_DIR}"

echo "== provision-portable-python: verifying installed Python version =="
ACTUAL_VERSION="$("${INSTALL_DIR}/python/bin/python3.13" --version 2>&1 | awk '{print $2}')"
if [ "${ACTUAL_VERSION}" != "${EXPECTED_PYTHON_VERSION}" ]; then
  echo "WRONG PYTHON VERSION: expected ${EXPECTED_PYTHON_VERSION}, got ${ACTUAL_VERSION}" >&2
  exit 1
fi
echo "  OK   Python ${ACTUAL_VERSION}"

echo "== provision-portable-python: verifying deployment target =="
ACTUAL_MINOS="$(otool -l "${INSTALL_DIR}/python/bin/python3.13" | awk '/LC_BUILD_VERSION/{f=1} f && /minos/{print $2; exit}')"
if [ "${ACTUAL_MINOS}" != "11.0" ]; then
  echo "unexpected deployment target: expected 11.0, got ${ACTUAL_MINOS}" >&2
  echo "(this does not necessarily fail provisioning, but the bundle-floor" >&2
  echo "assumption of 11.1 documented in BUILD-026-M11-PORTABLE-PYTHON-EVALUATION.md" >&2
  echo "may no longer hold — investigate before trusting minimumSystemVersion=11.1)" >&2
fi
echo "  minos=${ACTUAL_MINOS}"

echo "== provision-portable-python: PASS — ${INSTALL_DIR}/python/bin/python3.13 ready =="
