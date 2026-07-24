#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="${1:-$ROOT_DIR/dist/ZeroRodCAD Desktop.app}"
EXECUTABLE="$APP_PATH/Contents/MacOS/ZeroRodCAD Desktop"

if [[ ! -x "$EXECUTABLE" ]]; then
  echo "Packaged executable not found:"
  echo "  $EXECUTABLE"
  exit 1
fi

echo "1/7 Diagnostics"
"$EXECUTABLE" --diagnose

echo
echo "2/7 Headless GUI startup"
QT_QPA_PLATFORM=offscreen "$EXECUTABLE" --startup-test

echo
echo "3/7 Source preview engine"
source "$ROOT_DIR/.venv-packaging/bin/activate"
python "$ROOT_DIR/scripts/verify_preview_engine.py"

echo
echo "4/7 Bundle metadata"
plutil -lint "$APP_PATH/Contents/Info.plist"

echo
echo "5/7 Bundle size"
"$ROOT_DIR/scripts/report_macos_bundle.sh" "$APP_PATH"

echo
echo "6/7 Suspect dependency report"
"$ROOT_DIR/scripts/report_suspect_dependencies.sh" "$APP_PATH"

echo
echo "7/7 Launch"
open "$APP_PATH"

echo
echo "Automated verification commands passed."
echo "Manually confirm preview and STL/STEP export."
echo "Application log: ~/Library/Logs/ZeroRodCAD/zerorodcad.log"
