from __future__ import annotations

from pathlib import PurePosixPath

from .models import BundleSection


def classify_section(relative_path: str, *, is_macho: bool) -> BundleSection:
    """Classify a bundle path using stable, human-readable categories."""

    path = PurePosixPath(relative_path)
    parts = tuple(part.casefold() for part in path.parts)
    joined = "/".join(parts)

    if "vtkmodules" in parts:
        return BundleSection.VTK
    if "pyside6" in parts:
        return BundleSection.PYSIDE
    if "ocp" in parts or "/ocp/" in f"/{joined}/":
        return BundleSection.OCP
    if "casadi" in parts:
        return BundleSection.CASADI
    if any(part.startswith("qt") for part in parts):
        return BundleSection.QT
    if parts[:2] == ("contents", "macos"):
        return BundleSection.MACOS
    if parts[:2] == ("contents", "frameworks"):
        return BundleSection.FRAMEWORKS
    if parts[:2] == ("contents", "resources"):
        return BundleSection.RESOURCES
    if parts[:2] in {
        ("contents", "plugins"),
        ("contents", "plug-ins"),
    }:
        return BundleSection.PLUGINS
    if path.suffix.casefold() in {".py", ".pyc", ".pyo"}:
        return BundleSection.PYTHON
    if is_macho:
        return BundleSection.EXECUTABLES
    return BundleSection.OTHER
