"""Import probe used to validate the minimal packaging environment."""

from __future__ import annotations

import importlib

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


def main() -> int:
    failures: list[str] = []

    for module_name in MODULES:
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
