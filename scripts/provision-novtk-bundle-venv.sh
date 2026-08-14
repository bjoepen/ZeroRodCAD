#!/usr/bin/env bash
# Build 026 Finalization — single, authoritative, reproducible provisioning
# entry point for the shared No-VTK packaging venv (.venv-novtk-bundle) that
# both the productive Tauri sidecar build
# (scripts/build-productive-desktop-app.sh) and the legacy PySide6 TE-001.2
# validation script depend on.
#
# Replaces the previous implicit provisioning (embedded inline in
# scripts/validate-te0012-novtk-bundle.sh, which copied an already-patched
# CadQuery out of a separate, undocumented local venv). This script installs
# a pinned, vanilla dependency set from scratch and applies the tracked
# No-VTK patch via scripts/apply-cadquery-novtk-patch.sh — no dependency on
# any other local venv's state.
#
# Build 026 Finalization: the venv's own Python interpreter is now the
# pinned, portable astral-sh/python-build-standalone CPython 3.13
# (scripts/provision-portable-python.sh) rather than whatever `python3.13`
# happens to be on PATH — Homebrew's bottle floats its own
# MACOSX_DEPLOYMENT_TARGET to match the build machine's current OS, which was
# the root cause of Build 026 M1's honest-but-inflated 26.0 floor finding
# (see docs/migration/BUILD-026-M11-PORTABLE-PYTHON-EVALUATION.md). No
# Homebrew/system Python is used or required anywhere in this script.
#
# Usage: scripts/provision-novtk-bundle-venv.sh [venv-path]
#   venv-path defaults to .venv-novtk-bundle
set -euo pipefail

cd "$(dirname "$0")/.."

BUNDLE_VENV="${1:-.venv-novtk-bundle}"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"
PORTABLE_PYTHON_DIR=".portable-python-3.13"
PORTABLE_PYTHON="${PORTABLE_PYTHON_DIR}/python/bin/python3.13"

echo "== provision-novtk-bundle-venv: provisioning the pinned portable Python =="
scripts/provision-portable-python.sh "${PORTABLE_PYTHON_DIR}"

echo "== provision-novtk-bundle-venv: preparing isolated venv (${BUNDLE_VENV}) =="
if [ ! -x "${BUNDLE_PYTHON}" ]; then
  "${PORTABLE_PYTHON}" -m venv "${BUNDLE_VENV}"
fi

"${BUNDLE_PYTHON}" - <<'PY'
import sys
assert sys.prefix != sys.base_prefix, "venv is not isolated from the base interpreter"
print("prefix:", sys.prefix)
print("version:", sys.version)
PY

echo "== provision-novtk-bundle-venv: installing pinned dependencies (skipped if cadquery already present) =="
if ! "${BUNDLE_PYTHON}" -m pip show cadquery >/dev/null 2>&1; then
  "${BUNDLE_PYTHON}" -m pip install --upgrade pip
  "${BUNDLE_PYTHON}" -m pip install "cadquery-ocp-novtk==7.9.3.1.1"
  "${BUNDLE_PYTHON}" -m pip install "cadquery==2.8.0" --no-deps
  # Build 026 M1: casadi/runtype/scipy/numba were previously installed with
  # no version pin at all (any version pip resolved at install time). Pinned
  # here to the exact versions the productive bundle has been validated
  # against (see BUILD-026-M1-PRODUCTION-BUNDLE-HARDENING.md). scipy/numba
  # are still excluded from the final PyInstaller bundle (unchanged
  # packaging-spec exclude rule) — pinning here is about build-venv
  # reproducibility, not about shipping them.
  "${BUNDLE_PYTHON}" -m pip install \
    "ezdxf>=1.3.0" "multimethod<2.0,>=1.11" "nlopt<3.0,>=2.9.0" \
    "runtype==0.5.3" "casadi==3.7.2" "scipy==1.18.0" "numba==0.66.0" \
    "pyparsing>=3.0.0"
  "${BUNDLE_PYTHON}" -m pip install "PySide6>=6.7,<7" "PyInstaller==6.22.0"
  "${BUNDLE_PYTHON}" -m pip install -e . --no-deps
fi

# Build 026 Finalization: PyPI publishes numpy 2.4.6 as BOTH a
# macosx_11_0_arm64 and a macosx_14_0_arm64 wheel for the identical release
# — pip's default platform-tag resolution silently picks the newer/higher
# one when run on a machine reporting macOS >=14 (i.e. this build machine),
# which would otherwise re-introduce a 14.0 floor into an otherwise-11.x
# bundle. Explicitly select and force-install the 11.0-tagged wheel, proven
# byte-identical in function to the default one
# (docs/migration/BUILD-026-M11-PORTABLE-PYTHON-EVALUATION.md). `pip
# install --platform` is refused for a live-environment install, so the
# wheel is downloaded to a local file first, then installed by path.
echo "== provision-novtk-bundle-venv: pinning numpy to the macosx_11_0_arm64 wheel (not the default macosx_14_0_arm64 one) =="
NUMPY_WHEEL_DIR="build/downloads/numpy-macosx-11"
NUMPY_VERSION="2.4.6"
NUMPY_WHEEL="numpy-${NUMPY_VERSION}-cp313-cp313-macosx_11_0_arm64.whl"
mkdir -p "${NUMPY_WHEEL_DIR}"
if [ ! -f "${NUMPY_WHEEL_DIR}/${NUMPY_WHEEL}" ]; then
  "${BUNDLE_PYTHON}" -m pip download --no-deps --only-binary=:all: \
    --platform macosx_11_0_arm64 --python-version 313 --implementation cp --abi cp313 \
    -d "${NUMPY_WHEEL_DIR}" "numpy==${NUMPY_VERSION}"
fi
"${BUNDLE_PYTHON}" -m pip install --force-reinstall --no-deps "${NUMPY_WHEEL_DIR}/${NUMPY_WHEEL}"
INSTALLED_NUMPY_MINOS="$("${BUNDLE_PYTHON}" -c "
import numpy, subprocess, re, os
so = os.path.join(os.path.dirname(numpy.__file__), '_core', '_multiarray_umath.cpython-313-darwin.so')
out = subprocess.run(['otool', '-l', so], capture_output=True, text=True).stdout
m = re.search(r'LC_BUILD_VERSION.*?minos ([\d.]+)', out, re.S)
print(m.group(1) if m else 'UNKNOWN')
")"
if [ "${INSTALLED_NUMPY_MINOS}" != "11.0" ]; then
  echo "numpy did not install with the expected macosx_11_0_arm64 build (minos=${INSTALLED_NUMPY_MINOS})" >&2
  exit 1
fi
echo "  OK   numpy ${NUMPY_VERSION} installed at minos=11.0"

echo "== provision-novtk-bundle-venv: applying the tracked No-VTK patch =="
scripts/apply-cadquery-novtk-patch.sh "${BUNDLE_PYTHON}"

echo "== provision-novtk-bundle-venv: package audit =="
"${BUNDLE_PYTHON}" -m pip show cadquery cadquery-ocp-novtk PySide6 pyinstaller
if "${BUNDLE_PYTHON}" -m pip show cadquery-ocp >/dev/null 2>&1; then
  echo "cadquery-ocp is installed in ${BUNDLE_VENV} — this must not happen" >&2
  exit 1
fi
if "${BUNDLE_PYTHON}" -m pip show vtk >/dev/null 2>&1; then
  echo "vtk is installed in ${BUNDLE_VENV} — this must not happen" >&2
  exit 1
fi
"${BUNDLE_PYTHON}" -m pip check || true  # expected metadata-naming mismatch, see TE-001 Experiment.md

echo "== provision-novtk-bundle-venv: PASS — ${BUNDLE_VENV} is provisioned and No-VTK-patched =="
