"""Import probe used to validate the minimal packaging environment."""

from __future__ import annotations

import importlib
import os

MODULES = (
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "cadquery",
    "cadquery.occ_impl.exporters",
    "OCP",
    "vtkmodules.vtkCommonCore",
    "vtkmodules.vtkCommonDataModel",
    "zerorodcad.parameters",
    "zerorodcad.model",
    "zerorodcad.preview",
    "zerorodcad.export",
    "zerorodcad_desktop.app",
)

# TE-001.2: opt-in escape hatch for the no-VTK packaging environment, where
# vtkmodules is intentionally absent. Default behavior (env var unset) is
# unchanged for the normal VTK-based packaging pipeline.
_SKIP_VTK_ENV = "ZERORODCAD_SKIP_VTK_PROBE"


def main() -> int:
    failures: list[str] = []
    modules = MODULES
    if os.environ.get(_SKIP_VTK_ENV):
        modules = tuple(name for name in MODULES if not name.startswith("vtkmodules"))
        print(f"{_SKIP_VTK_ENV} set: skipping vtkmodules.* checks\n")

    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print(f"OK   {module_name}")
        except Exception as exc:
            failures.append(f"{module_name}: {exc}")
            print(f"FAIL {module_name}: {exc}")

    if failures:
        print("\nImport probe failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nAll required runtime imports succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
