#!/usr/bin/env bash
# TE-001.2 No-VTK production bundle validation. Never touches the productive .venv.
set -euo pipefail

cd "$(dirname "$0")/.."

REPORT_DIR="build/reports/te0012-novtk-bundle"
BUNDLE_VENV=".venv-novtk-bundle"
BUNDLE_PYTHON="${BUNDLE_VENV}/bin/python"
APP_PATH="dist/ZeroRodCAD Desktop.app"
POC_PATCH_SOURCE=".venv-novtk-poc/lib/python3.13/site-packages/cadquery"
PATCH_TARGET="${BUNDLE_VENV}/lib/python3.13/site-packages/cadquery"

echo "== TE-001.2: verifying Python 3.13 =="
if ! command -v python3.13 >/dev/null 2>&1; then
  echo "python3.13 not found on PATH" >&2
  exit 1
fi
python3.13 -c "import sys; assert sys.version_info[:2] == (3, 13), sys.version" \
  || { echo "python3.13 did not report version 3.13.x" >&2; exit 1; }

echo "== TE-001.2: preparing isolated packaging venv (${BUNDLE_VENV}) =="
if [ ! -x "${BUNDLE_PYTHON}" ]; then
  python3.13 -m venv "${BUNDLE_VENV}"
fi

echo "== TE-001.2: verifying venv isolation (no system-site-packages) =="
"${BUNDLE_PYTHON}" - <<'PY'
import sys
assert sys.prefix != sys.base_prefix, "venv is not isolated from the base interpreter"
print("prefix:", sys.prefix)
print("version:", sys.version)
PY

echo "== TE-001.2: installing pinned dependencies (skipped if cadquery already present) =="
if ! "${BUNDLE_PYTHON}" -c "import cadquery" >/dev/null 2>&1; then
  "${BUNDLE_PYTHON}" -m pip install --upgrade pip
  "${BUNDLE_PYTHON}" -m pip install "cadquery-ocp-novtk==7.9.3.1.1"
  "${BUNDLE_PYTHON}" -m pip install "cadquery==2.8.0" --no-deps
  "${BUNDLE_PYTHON}" -m pip install \
    "ezdxf>=1.3.0" "multimethod<2.0,>=1.11" "nlopt<3.0,>=2.9.0" "runtype" "casadi" \
    "pyparsing>=3.0.0" "scipy" "numba"
  "${BUNDLE_PYTHON}" -m pip install "PySide6>=6.7,<7" "PyInstaller>=6.16,<7"
  "${BUNDLE_PYTHON}" -m pip install -e . --no-deps
fi

echo "== TE-001.2: applying TE-001.1 patch (reused verbatim, not redesigned) =="
if [ ! -d "${POC_PATCH_SOURCE}" ]; then
  echo "TE-001.1's patched cadquery copy (.venv-novtk-poc) was not found." >&2
  echo "Run scripts/validate-te001-novtk.sh first to (re)create it, then re-run this script." >&2
  exit 1
fi
cp "${POC_PATCH_SOURCE}/occ_impl/shapes.py" "${PATCH_TARGET}/occ_impl/shapes.py"
cp "${POC_PATCH_SOURCE}/occ_impl/exporters/vtk.py" "${PATCH_TARGET}/occ_impl/exporters/vtk.py"
cp "${POC_PATCH_SOURCE}/occ_impl/assembly.py" "${PATCH_TARGET}/occ_impl/assembly.py"
cp "${POC_PATCH_SOURCE}/occ_impl/exporters/assembly.py" "${PATCH_TARGET}/occ_impl/exporters/assembly.py"
"${BUNDLE_PYTHON}" - <<'PY'
import sys
sys.path.insert(0, ".")
from tools.poc.novtk.vtk_import_blocker import install
install()
import cadquery
print("TE-001.1 patch active: import cadquery succeeded under VTKImportBlocker ->", cadquery.__version__)
PY

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
