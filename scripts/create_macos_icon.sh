#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT_DIR/assets/app-icon-1024.png"
ICONSET="$ROOT_DIR/build/ZeroRodCAD.iconset"
OUTPUT_DIR="$ROOT_DIR/assets/macos"
OUTPUT="$OUTPUT_DIR/ZeroRodCAD.icns"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Icon creation requires macOS tools: sips and iconutil."
  exit 1
fi

if [[ ! -f "$SOURCE" ]]; then
  echo "Missing source icon: $SOURCE"
  exit 1
fi

rm -rf "$ICONSET"
mkdir -p "$ICONSET" "$OUTPUT_DIR"

sips -z 16 16 "$SOURCE" --out "$ICONSET/icon_16x16.png" >/dev/null
sips -z 32 32 "$SOURCE" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$SOURCE" --out "$ICONSET/icon_32x32.png" >/dev/null
sips -z 64 64 "$SOURCE" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$SOURCE" --out "$ICONSET/icon_128x128.png" >/dev/null
sips -z 256 256 "$SOURCE" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$SOURCE" --out "$ICONSET/icon_256x256.png" >/dev/null
sips -z 512 512 "$SOURCE" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$SOURCE" --out "$ICONSET/icon_512x512.png" >/dev/null
cp "$SOURCE" "$ICONSET/icon_512x512@2x.png"

iconutil -c icns "$ICONSET" -o "$OUTPUT"
echo "Created $OUTPUT"
