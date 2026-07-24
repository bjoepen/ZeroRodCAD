#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PACKAGING_VENV="${PACKAGING_VENV:-.venv-packaging}"

rm -rf "$PACKAGING_VENV"
"$PYTHON_BIN" -m venv "$PACKAGING_VENV"
source "$PACKAGING_VENV/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r packaging/macos/requirements-build.txt

echo
echo "Clean packaging environment created:"
echo "  $PACKAGING_VENV"
echo
python -m pip list
echo
python scripts/runtime_import_probe.py
