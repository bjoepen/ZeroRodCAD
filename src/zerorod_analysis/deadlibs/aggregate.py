"""Aggregate bundle files into logical library units."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path, PurePosixPath

from ..scanner import BundleDatabase
from .models import FindingCategory, LibraryUnit


def _framework_key(relative_path: str) -> str | None:
    parts = PurePosixPath(relative_path).parts
    for index, part in enumerate(parts):
        if part.endswith(".framework"):
            return "/".join(parts[: index + 1])
    return None


def _python_package_key(relative_path: str) -> str | None:
    parts = PurePosixPath(relative_path).parts
    if "site-packages" not in parts:
        return None
    index = parts.index("site-packages") + 1
    if index >= len(parts):
        return None
    top_level = parts[index]
    if top_level.endswith((".dist-info", ".data")):
        top_level = top_level.rsplit("-", 1)[0]
    return "/".join(parts[:index] + (top_level,))


def _unit_identity(relative_path: str) -> tuple[str, FindingCategory] | None:
    framework = _framework_key(relative_path)
    if framework:
        return framework, FindingCategory.FRAMEWORK

    path = PurePosixPath(relative_path)
    if path.suffix in {".dylib", ".so"}:
        return relative_path, FindingCategory.DYLIB

    python_package = _python_package_key(relative_path)
    if python_package:
        return python_package, FindingCategory.PYTHON_PACKAGE

    return None


def aggregate_library_units(database: BundleDatabase) -> tuple[LibraryUnit, ...]:
    grouped_paths: dict[tuple[str, FindingCategory], list[Path]] = defaultdict(list)
    grouped_sizes: dict[tuple[str, FindingCategory], int] = defaultdict(int)

    for item in database.files:
        identity = _unit_identity(item.relative_path)
        if identity is None:
            continue
        grouped_paths[identity].append(Path(item.relative_path))
        if not item.is_symlink:
            grouped_sizes[identity] += item.size_bytes

    units = [
        LibraryUnit(
            identifier=identifier,
            paths=sorted(paths, key=lambda path: path.as_posix()),
            size_bytes=grouped_sizes[(identifier, category)],
            category=category,
        )
        for (identifier, category), paths in grouped_paths.items()
    ]
    return tuple(sorted(units, key=lambda unit: unit.identifier.casefold()))
