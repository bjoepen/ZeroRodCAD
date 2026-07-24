#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script must run on macOS."
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  echo "No .venv found. Run scripts/bootstrap_macos.sh first."
  exit 1
fi

source .venv/bin/activate
python -m pip install -e ".[dev,desktop,packaging]"

"$ROOT_DIR/scripts/create_macos_icon.sh"

rm -rf build dist
pyinstaller --noconfirm --clean packaging/macos/ZeroRodCAD.spec

APP_PATH="$ROOT_DIR/dist/ZeroRodCAD Desktop.app"

echo
echo "Application created:"
echo "  $APP_PATH"
echo
echo "Run diagnostics:"
echo "  \"$APP_PATH/Contents/MacOS/ZeroRodCAD Desktop\" --diagnose"
echo
echo "Open the app:"
echo "  open \"$APP_PATH\""
