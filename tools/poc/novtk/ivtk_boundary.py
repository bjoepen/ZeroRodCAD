"""TE-001 IVtk boundary test (section 18).

Attempts to import OCP's VTK-bridge submodules directly, *without* the
VTKImportBlocker installed (per the mandate: this boundary is investigated
separately, not blocked). Classifies each module as:

  A - ImportError without any VTK load (acceptable)
  B - import succeeds without any VTK load (acceptable)
  unacceptable - real VTK gets loaded (must be documented in detail)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

IVTK_MODULES = ("OCP.IVtk", "OCP.IVtkOCC", "OCP.IVtkTools", "OCP.IVtkVTK")


def _vtk_modules_loaded() -> list[str]:
    return sorted(
        name for name in sys.modules if name.split(".", 1)[0].lower() in {"vtk", "vtkmodules"}
    )


def probe(module_name: str) -> dict:
    before = _vtk_modules_loaded()
    try:
        __import__(module_name)
        after = _vtk_modules_loaded()
        new_vtk = sorted(set(after) - set(before))
        classification = "unacceptable-vtk-loaded" if new_vtk else "B-import-succeeded-no-vtk"
        return {
            "module": module_name,
            "result": "import-succeeded",
            "classification": classification,
            "new_vtk_modules": new_vtk,
        }
    except Exception as exc:
        after = _vtk_modules_loaded()
        new_vtk = sorted(set(after) - set(before))
        classification = "unacceptable-vtk-loaded" if new_vtk else "A-importerror-no-vtk"
        return {
            "module": module_name,
            "result": f"{type(exc).__name__}: {exc}",
            "classification": classification,
            "new_vtk_modules": new_vtk,
        }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="TE-001 IVtk boundary probe")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    results = [probe(name) for name in IVTK_MODULES]
    unacceptable = [r for r in results if r["classification"] == "unacceptable-vtk-loaded"]

    report = {
        "schema": "zerorodcad/te001-novtk-ivtk-boundary/v1",
        "results": results,
        "sys_modules_vtk_hits_final": _vtk_modules_loaded(),
        "overall": "unacceptable" if unacceptable else "acceptable",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"IVtk boundary report written to: {args.report}")
    return 0 if not unacceptable else 1


if __name__ == "__main__":
    raise SystemExit(main())
