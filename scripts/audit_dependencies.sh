#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PACKAGING_VENV="${PACKAGING_VENV:-.venv-packaging}"
REPORT_DIR="$ROOT_DIR/build/reports/dependencies"

if [[ ! -x "$PACKAGING_VENV/bin/python" ]]; then
  echo "Packaging environment not found: $PACKAGING_VENV"
  echo "Run: make packaging-venv"
  exit 1
fi

mkdir -p "$REPORT_DIR"
source "$PACKAGING_VENV/bin/activate"

python -m pip install \
  -r packaging/macos/requirements-audit.txt

python -m pip freeze \
  | LC_ALL=C sort \
  > "$REPORT_DIR/pip-freeze.txt"

pipdeptree \
  --warn silence \
  > "$REPORT_DIR/pipdeptree.txt"

pipdeptree \
  --warn silence \
  --json-tree \
  > "$REPORT_DIR/pipdeptree.json"

python scripts/runtime_import_probe.py \
  | tee "$REPORT_DIR/runtime-import-probe.txt"

python - <<'PY' > "$REPORT_DIR/distribution-sizes.txt"
from importlib import metadata
from pathlib import Path

rows = []
for distribution in metadata.distributions():
    files = distribution.files or ()
    total = 0
    for file in files:
        try:
            location = Path(distribution.locate_file(file))
            if location.is_file():
                total += location.stat().st_size
        except OSError:
            pass
    rows.append((total, distribution.metadata.get("Name", "unknown"), distribution.version))

for total, name, version in sorted(rows, reverse=True):
    print(f"{total / 1024 / 1024:10.1f} MiB  {name} {version}")
PY

echo
echo "Dependency audit written to:"
echo "  $REPORT_DIR"
