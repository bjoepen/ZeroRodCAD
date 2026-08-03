from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..macho import macho_id, otool_dependencies
from ..models import DuplicateGroup

CANONICAL_PREFIX = "Contents/Frameworks/"


@dataclass(frozen=True)
class DeduplicationAction:
    sha256: str
    keep: str
    candidates_for_removal: tuple[str, ...]
    size_bytes: int
    redundant_bytes: int
    dependencies_checked: bool
    safe_to_apply_automatically: bool
    reason: str


def choose_canonical(group: DuplicateGroup) -> Path:
    root_frameworks = [
        item.path
        for item in group.files
        if item.relative_path.startswith(CANONICAL_PREFIX)
        and "/__dot__dylibs/" not in item.relative_path
        and item.relative_path.count("/") == 2
    ]
    if root_frameworks:
        return sorted(root_frameworks)[0]

    frameworks = [
        item.path for item in group.files if item.relative_path.startswith(CANONICAL_PREFIX)
    ]
    if frameworks:
        return sorted(frameworks)[0]

    return sorted(item.path for item in group.files)[0]


def create_plan(groups: list[DuplicateGroup]) -> list[DeduplicationAction]:
    actions: list[DeduplicationAction] = []

    for group in groups:
        keep = choose_canonical(group)
        removals = tuple(str(item.path) for item in group.files if item.path != keep)

        keep_id = macho_id(keep)
        keep_dependencies = set(otool_dependencies(keep))
        compatible = True

        for item in group.files:
            if item.path == keep:
                continue
            if macho_id(item.path) != keep_id:
                compatible = False
            if set(otool_dependencies(item.path)) != keep_dependencies:
                compatible = False

        actions.append(
            DeduplicationAction(
                sha256=group.sha256,
                keep=str(keep),
                candidates_for_removal=removals,
                size_bytes=group.size_bytes,
                redundant_bytes=group.redundant_bytes,
                dependencies_checked=True,
                safe_to_apply_automatically=False,
                reason=(
                    "Byteidentisch und Mach-O-Metadaten identisch; "
                    "dennoch ist eine automatische Entfernung ohne "
                    "vollständige Loader- und Laufzeitvalidierung gesperrt."
                    if compatible
                    else ("Byteidentisch, aber Mach-O-ID oder Abhängigkeiten unterscheiden sich.")
                ),
            )
        )

    return actions
