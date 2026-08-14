#!/usr/bin/env bash
# Build 026 M1 — single, authoritative, reproducible provisioning entry point
# for the shared No-VTK packaging venv (.venv-novtk-bundle) that both the
# productive Tauri sidecar build (scripts/build-productive-desktop-app.sh)
# and the legacy PySide6 TE-001.2 validation script depend on.
#
# Replaces the previous implicit provisioning (embedded inline in
# scripts/validate-te0012-novtk-bundle.sh, which copied an already-patched
# CadQuery out of a separate, undocumented local venv). This script installs
# a pinned, vanilla dependency set from scratch and applies the tracked
# No-VTK patch via scripts/apply-cadquery-novtk-patch.sh — no dependency on
# any other local venv's state.
#
# Usage: scripts/provision-novtk-bundle-venv.sh [venv-path]
#   venv-path defaults to .venv-novtk-bundle
set -euo pipefail

cd "$(dirname "$0")/.."

BUNDLE_VENV="${1:-.venv-novtk-bundle}"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"

echo "== provision-novtk-bundle-venv: verifying Python 3.13 =="
if ! command -v python3.13 >/dev/null 2>&1; then
  echo "python3.13 not found on PATH" >&2
  exit 1
fi
python3.13 -c "import sys; assert sys.version_info[:2] == (3, 13), sys.version" \
  || { echo "python3.13 did not report version 3.13.x" >&2; exit 1; }

echo "== provision-novtk-bundle-venv: preparing isolated venv (${BUNDLE_VENV}) =="
if [ ! -x "${BUNDLE_PYTHON}" ]; then
  python3.13 -m venv "${BUNDLE_VENV}"
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
  "${BUNDLE_PYTHON}" -m pip install "PySide6>=6.7,<7" "PyInstaller>=6.16,<7"
  "${BUNDLE_PYTHON}" -m pip install -e . --no-deps
fi

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
