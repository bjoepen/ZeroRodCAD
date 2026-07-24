#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_PATH="$ROOT_DIR/dist/ZeroRodCAD Desktop.app"
RELEASE_DIR="$ROOT_DIR/release"
ARCHIVE="$RELEASE_DIR/ZeroRodCAD-Desktop-0.12.0-macOS.zip"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Application not found. Run scripts/build_macos_app.sh first."
  exit 1
fi

mkdir -p "$RELEASE_DIR"
rm -f "$ARCHIVE"

ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ARCHIVE"

echo "Release archive created:"
echo "  $ARCHIVE"
