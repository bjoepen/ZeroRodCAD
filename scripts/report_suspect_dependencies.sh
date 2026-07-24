#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:-dist/ZeroRodCAD Desktop.app}"
REPORT_DIR="build/reports"
REPORT="$REPORT_DIR/suspect-dependencies.txt"

mkdir -p "$REPORT_DIR"

{
  echo "ZeroRodCAD suspect dependency report"
  echo "Application: $APP_PATH"
  echo
  for name in casadi llvmlite numba vtkmodules scipy matplotlib pandas IPython jupyter; do
    echo "## $name"
    find "$APP_PATH" -iname "*$name*" -print 2>/dev/null || true
    echo
  done
} | tee "$REPORT"
