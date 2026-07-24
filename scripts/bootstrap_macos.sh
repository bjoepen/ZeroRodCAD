#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python was not found."
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop,packaging]"
pre-commit install

echo
echo "Setup complete."
echo "Activate with: source .venv/bin/activate"
echo "Run quality gate with: make quality"
echo "Start app with: zerorodcad-desktop"
echo "Build .app with: make macos-app"
