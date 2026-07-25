from __future__ import annotations

import atexit
import runpy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

REPORT_DIR = PROJECT_ROOT / "build" / "reports" / "sprint3-phase3-vtk-analysis"
REPORT_FILE = REPORT_DIR / "vtkmodules-runtime-loaded.txt"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def write_report() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    loaded_modules = sorted(
        name for name in sys.modules if name == "vtkmodules" or name.startswith("vtkmodules.")
    )

    REPORT_FILE.write_text(
        "\n".join(loaded_modules) + "\n",
        encoding="utf-8",
    )

    print(f"\nVTK runtime report written to:\n{REPORT_FILE}")
    print(f"Loaded VTK modules: {len(loaded_modules)}")


atexit.register(write_report)

runpy.run_module(
    "zerorodcad_desktop.launcher",
    run_name="__main__",
)
