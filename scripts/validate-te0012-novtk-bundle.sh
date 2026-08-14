#!/usr/bin/env bash
# TE-001.2 No-VTK production bundle validation. Never touches the productive .venv.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/te0012-novtk-bundle"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"
APP_PATH="dist/ZeroRodCAD Desktop.app"

echo "== TE-001.2: provisioning the shared No-VTK packaging venv (${BUNDLE_VENV}) =="
# Build 026 M1: venv creation, pinned-dependency install, and the CadQuery
# No-VTK patch application are now a single, reusable, reproducible script
# (no longer an undocumented copy from .venv-novtk-poc — see
# docs/migration/BUILD-026-M1-PRODUCTION-BUNDLE-HARDENING.md).
scripts/provision-novtk-bundle-venv.sh "${BUNDLE_VENV}"

echo "== TE-001.2: pre-build package audit =="
"${BUNDLE_PYTHON}" -m pip list
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

echo "== TE-001.2: pre-build functional sanity check =="
mkdir -p "${REPORT_DIR}"
"${BUNDLE_PYTHON}" tools/poc/novtk/run_checkpoints.py \
  --report "${REPORT_DIR}/pre-build-checkpoints.json" \
  --raw-trace "${REPORT_DIR}/pre-build-raw-trace.jsonl"

echo "== TE-001.2: building the app bundle (ZERORODCAD_NOVTK_BUNDLE=1) =="
rm -rf "build/ZeroRodCAD" "dist"
ZERORODCAD_SKIP_VTK_PROBE=1 "${BUNDLE_PYTHON}" scripts/runtime_import_probe.py
ZERORODCAD_NOVTK_BUNDLE=1 "${BUNDLE_VENV}/bin/pyinstaller" --noconfirm --clean --log-level INFO \
  packaging/macos/ZeroRodCAD.spec 2>&1 | tee "${REPORT_DIR}/pyinstaller-build.log"

if [ ! -d "${APP_PATH}" ]; then
  echo "Bundle build failed: ${APP_PATH} does not exist" >&2
  exit 1
fi

echo "== TE-001.2: static bundle analysis (existing Scanner 2.0 tooling) =="
if [ -x ".venv/bin/python" ]; then
  SCAN_PYTHON=".venv/bin/python"
else
  SCAN_PYTHON="python3.13"
fi
"${SCAN_PYTHON}" tools/scan_bundle.py "${APP_PATH}" \
  --output-dir "${REPORT_DIR}/scan" --dead-libraries --macho-dependencies --no-cache

echo "== TE-001.2: explicit VTK search =="
VTK_FILES=$(find "${APP_PATH}" -iname "*vtk*" -o -iname "*IVtk*")
if [ -n "${VTK_FILES}" ]; then
  echo "VTK-related files found in bundle:" >&2
  echo "${VTK_FILES}" >&2
  exit 1
fi
echo "0 VTK-related files found in bundle (find -iname '*vtk*' / '*IVtk*')"

echo "== TE-001.2: app startup smoke test =="
QT_QPA_PLATFORM=offscreen "${APP_PATH}/Contents/MacOS/ZeroRodCAD Desktop" --startup-test

echo "== TE-001.2: PoC test suite =="
"${SCAN_PYTHON}" -m pytest tests/poc/novtk/ -v

echo "== TE-001.2: ruff check =="
"${SCAN_PYTHON}" -m ruff check tools/poc/novtk tests/poc/novtk scripts/runtime_import_probe.py

echo "== TE-001.2: ruff format check =="
"${SCAN_PYTHON}" -m ruff format --check tools/poc/novtk tests/poc/novtk scripts/runtime_import_probe.py

echo "TE-001.2 No-VTK production bundle evaluation completed."
BUNDLE_VTK_BYTES=$("${SCAN_PYTHON}" -c "
import json
data = json.load(open('${REPORT_DIR}/scan/scanner2/scanner2-inventory.json'))
print(data['statistics']['section_sizes'].get('VTK', 0))
")
if [ "${BUNDLE_VTK_BYTES}" = "0" ]; then
  echo "Gate C: PASS"
else
  echo "Gate C: FAIL (VTK section size = ${BUNDLE_VTK_BYTES} bytes)"
fi
