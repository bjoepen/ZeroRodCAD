#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="$ROOT_DIR/dist/ZeroRodCAD Desktop.app"
EXECUTABLE="$APP_PATH/Contents/MacOS/ZeroRodCAD Desktop"

if [[ ! -x "$EXECUTABLE" ]]; then
  echo "Packaged executable not found:"
  echo "  $EXECUTABLE"
  exit 1
fi

echo "Running packaged diagnostics..."
"$EXECUTABLE" --diagnose

echo
echo "Inspecting bundle metadata..."
plutil -p "$APP_PATH/Contents/Info.plist"

echo
echo "Checking signature state..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH" || true

echo
echo "Opening application..."
open "$APP_PATH"
