from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath

from .models import BundleFile, BundleSection


@dataclass(frozen=True, slots=True)
class ScanFilter:
    """Optional post-scan selection rules."""

    include_sections: frozenset[BundleSection] = frozenset()
    exclude_sections: frozenset[BundleSection] = frozenset()
    extensions: frozenset[str] = frozenset()
    path_patterns: tuple[str, ...] = ()
    macho_only: bool = False

    def matches(self, item: BundleFile) -> bool:
        if self.include_sections and item.section not in self.include_sections:
            return False
        if item.section in self.exclude_sections:
            return False
        if self.extensions and item.extension.casefold() not in self.extensions:
            return False
        if self.macho_only and not item.is_macho:
            return False
        if self.path_patterns and not any(
            fnmatch(PurePosixPath(item.relative_path).as_posix(), pattern)
            for pattern in self.path_patterns
        ):
            return False
        return True


def normalize_extensions(values: list[str] | tuple[str, ...]) -> frozenset[str]:
    return frozenset(
        value.casefold() if value.startswith(".") else f".{value.casefold()}" for value in values
    )
