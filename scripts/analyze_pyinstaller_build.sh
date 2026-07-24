#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT_DIR="$ROOT_DIR/build/reports/pyinstaller"
mkdir -p "$REPORT_DIR"

WARN_FILE="$(find build -name 'warn-*.txt' -type f | head -n 1 || true)"
XREF_FILE="$(find build -name 'xref-*.html' -type f | head -n 1 || true)"
GRAPH_FILE="$(find build -name 'graph-*.dot' -type f | head -n 1 || true)"

if [[ -n "$WARN_FILE" ]]; then
  cp "$WARN_FILE" "$REPORT_DIR/"
fi

if [[ -n "$XREF_FILE" ]]; then
  cp "$XREF_FILE" "$REPORT_DIR/"
fi

if [[ -n "$GRAPH_FILE" ]]; then
  cp "$GRAPH_FILE" "$REPORT_DIR/"
fi

python - <<'PY'
from pathlib import Path

frameworks = Path("dist/ZeroRodCAD Desktop.app/Contents/Frameworks")
report = Path("build/reports/pyinstaller/framework-summary.txt")
report.parent.mkdir(parents=True, exist_ok=True)

lines = ["ZeroRodCAD framework summary", ""]
if not frameworks.exists():
    lines.append("Framework directory not found.")
else:
    entries = []
    for child in frameworks.iterdir():
        try:
            if child.is_dir():
                size = sum(
                    path.stat().st_size
                    for path in child.rglob("*")
                    if path.is_file()
                )
            else:
                size = child.stat().st_size
        except OSError:
            continue
        entries.append((size, child.name))

    for size, name in sorted(entries, reverse=True):
        lines.append(f"{size / 1024 / 1024:10.1f} MiB  {name}")

report.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print(report.read_text(encoding="utf-8"))
PY
