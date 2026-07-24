#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="${1:-$ROOT_DIR/dist/ZeroRodCAD Desktop.app}"
EXECUTABLE="$APP_PATH/Contents/MacOS/ZeroRodCAD Desktop"

if [[ ! -x "$EXECUTABLE" ]]; then
  echo "Packaged executable not found: $EXECUTABLE"
  exit 1
fi

echo "1/5 Diagnostics"
"$EXECUTABLE" --diagnose

echo
echo "2/5 Headless startup smoke test"
QT_QPA_PLATFORM=offscreen "$EXECUTABLE" --startup-test

echo
echo "3/5 Bundle metadata"
plutil -lint "$APP_PATH/Contents/Info.plist"

echo
echo "4/5 Bundle size"
"$ROOT_DIR/scripts/report_macos_bundle.sh" "$APP_PATH"

echo
echo "5/5 Launch"
open "$APP_PATH"

echo
echo "Verification commands passed."
echo "Application log: ~/Library/Logs/ZeroRodCAD/zerorodcad.log"
