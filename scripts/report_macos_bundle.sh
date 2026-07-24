#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:-dist/ZeroRodCAD Desktop.app}"
REPORT_DIR="build/reports"
REPORT="$REPORT_DIR/macos-bundle-size.txt"
ALL_FILES="$REPORT_DIR/macos-bundle-all-files.txt"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Application does not exist: $APP_PATH"
  exit 1
fi

mkdir -p "$REPORT_DIR"

find "$APP_PATH" -type f -print0 \
  | xargs -0 du -h \
  | sort -hr > "$ALL_FILES"

{
  echo "ZeroRodCAD macOS bundle size report"
  echo "Application: $APP_PATH"
  echo
  du -sh "$APP_PATH"
  echo
  echo "Largest files:"
  sed -n '1,50p' "$ALL_FILES"
} | tee "$REPORT"

SIZE_KB="$(du -sk "$APP_PATH" | awk '{print $1}')"
BUDGET_KB="${ZERORODCAD_APP_SIZE_BUDGET_KB:-1200000}"

if (( SIZE_KB > BUDGET_KB )); then
  echo
  echo "ERROR: bundle exceeds compatibility budget."
  echo "Measured: ${SIZE_KB} KB; budget: ${BUDGET_KB} KB."
  exit 1
fi

echo
echo "Bundle size recorded."
