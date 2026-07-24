#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.12 was not found. Install it first, for example with:"
  echo "  brew install python@3.12"
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"

echo
echo "Setup complete."
echo "Activate with: source .venv/bin/activate"
echo "Run tests with: pytest -v"
echo "Start app with: zerorodcad-desktop"
