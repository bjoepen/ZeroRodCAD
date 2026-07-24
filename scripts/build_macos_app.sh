#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script must run on macOS."
  exit 1
fi

PACKAGING_VENV="${PACKAGING_VENV:-.venv-packaging}"
MODE="${1:-release}"

if [[ ! -x "$PACKAGING_VENV/bin/python" ]]; then
  ./scripts/create_packaging_venv.sh
fi

source "$PACKAGING_VENV/bin/activate"
./scripts/create_macos_icon.sh
rm -rf build dist

if [[ "$MODE" == "debug" ]]; then
  pyinstaller --noconfirm --clean packaging/macos/ZeroRodCAD-Debug.spec
  APP_PATH="$ROOT_DIR/dist/ZeroRodCAD Desktop Debug.app"
else
  pyinstaller --noconfirm --clean packaging/macos/ZeroRodCAD.spec
  APP_PATH="$ROOT_DIR/dist/ZeroRodCAD Desktop.app"
fi

echo
echo "Application created: $APP_PATH"
du -sh "$APP_PATH"
./scripts/report_macos_bundle.sh "$APP_PATH"
