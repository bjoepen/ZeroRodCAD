"""Resolve usage evidence for aggregated bundle libraries."""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath

from ..macho import DependencyGraph
from ..scanner import BundleDatabase
from .confidence import assess_usage
from .models import (
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Reference,
    ReferenceKind,
    UsageRecord,
)


class DeadLibraryResolver:
    def resolve(
        self,
        units: Iterable[LibraryUnit],
        usage_by_library: Mapping[str, UsageRecord] | None = None,
        *,
        bundle_root: Path | None = None,
        total_bundle_size_bytes: int = 0,
    ) -> DeadLibraryAnalysisResult:
        usage_records = usage_by_library or {}
        findings: list[DeadLibraryFinding] = []

        for unit in sorted(units, key=lambda item: item.identifier.casefold()):
            usage = usage_records.get(unit.identifier, UsageRecord(unit.identifier))
            confidence, recommendation, reasons = assess_usage(usage, unit.category)
            if recommendation.value == "keep":
                category = FindingCategory.REFERENCED
            elif recommendation.value == "review":
                category = FindingCategory.POSSIBLY_UNUSED
            else:
                category = FindingCategory.UNUSED
            findings.append(
                DeadLibraryFinding(
                    library=unit,
                    usage=usage,
                    confidence=confidence,
                    category=category,
                    recommendation=recommendation,
                    reasons=reasons,
                )
            )

        return DeadLibraryAnalysisResult(
            findings=findings,
            bundle_root=bundle_root,
            total_bundle_size_bytes=total_bundle_size_bytes,
        )


def _unit_for_path(path: str, units: Iterable[LibraryUnit]) -> LibraryUnit | None:
    matches = [
        unit
        for unit in units
        if any(
            path == item.as_posix() or path.startswith(item.as_posix() + "/") for item in unit.paths
        )
    ]
    return max(matches, key=lambda unit: len(unit.identifier), default=None)


def _module_names(unit: LibraryUnit) -> set[str]:
    name = PurePosixPath(unit.identifier).name
    if name.endswith(".framework"):
        name = name.removesuffix(".framework")
    if name.endswith((".dylib", ".so")):
        name = name.split(".", 1)[0].removeprefix("lib")
    return {name, name.replace("-", "_"), name.casefold()}


def _python_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError):
        return set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def resolve_usage(
    database: BundleDatabase,
    graph: DependencyGraph,
    units: Iterable[LibraryUnit],
) -> dict[str, UsageRecord]:
    unit_list = tuple(units)
    records = {unit.identifier: UsageRecord(unit.identifier) for unit in unit_list}

    for source, targets in graph.edges.items():
        for target in targets:
            unit = _unit_for_path(target, unit_list)
            if unit is None:
                continue
            records[unit.identifier].references.append(
                Reference(
                    source=source,
                    target=unit.identifier,
                    kind=ReferenceKind.MACHO_DEPENDENCY,
                    detail=f"LC_LOAD_DYLIB resolves to {target}",
                )
            )

    import_index: dict[str, list[LibraryUnit]] = defaultdict(list)
    for unit in unit_list:
        for name in _module_names(unit):
            import_index[name.casefold()].append(unit)

    for item in database.files:
        if item.extension.casefold() != ".py":
            continue
        imports = _python_imports(item.path)
        for imported in imports:
            for unit in import_index.get(imported.casefold(), []):
                records[unit.identifier].references.append(
                    Reference(
                        source=item.relative_path,
                        target=unit.identifier,
                        kind=ReferenceKind.PYTHON_IMPORT,
                        detail=f"import {imported}",
                    )
                )

    for item in database.files:
        if item.extension.casefold() not in {".py", ".json", ".plist", ".conf"}:
            continue
        try:
            text = item.path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower_text = text.casefold()
        for unit in unit_list:
            names = _module_names(unit)
            if not any(name.casefold() in lower_text for name in names):
                continue
            if "importlib.import_module" in text or "dlopen" in lower_text:
                records[unit.identifier].references.append(
                    Reference(
                        source=item.relative_path,
                        target=unit.identifier,
                        kind=ReferenceKind.DYNAMIC_LOAD_HINT,
                        detail="Library name appears near a dynamic-loading API.",
                    )
                )

    return records
