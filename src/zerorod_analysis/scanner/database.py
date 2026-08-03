from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .filters import ScanFilter
from .models import BundleFile, BundleSection


@dataclass(frozen=True, slots=True)
class BundleStatistics:
    file_count: int
    directory_count: int
    total_size_bytes: int
    symlink_count: int
    macho_count: int
    python_count: int
    cache_hits: int
    cache_misses: int
    section_counts: dict[str, int]
    section_sizes: dict[str, int]


@dataclass(slots=True)
class BundleDatabase:
    """In-memory bundle index shared by later analysis stages."""

    root: Path
    files: tuple[BundleFile, ...]
    directory_count: int
    cache_hits: int = 0
    cache_misses: int = 0
    path_index: dict[str, BundleFile] = field(init=False)
    hash_index: dict[str, tuple[BundleFile, ...]] = field(init=False)
    extension_index: dict[str, tuple[BundleFile, ...]] = field(init=False)
    section_index: dict[BundleSection, tuple[BundleFile, ...]] = field(init=False)

    def __post_init__(self) -> None:
        self.path_index = {item.relative_path: item for item in self.files}
        self.hash_index = self._group_by(lambda item: item.sha256)
        self.extension_index = self._group_by(lambda item: item.extension.casefold())
        section_groups = self._group_by(lambda item: item.section)
        self.section_index = {section: section_groups.get(section, ()) for section in BundleSection}

    def _group_by(self, key_function):  # type: ignore[no-untyped-def]
        grouped: dict[object, list[BundleFile]] = defaultdict(list)
        for item in self.files:
            grouped[key_function(item)].append(item)
        return {key: tuple(values) for key, values in grouped.items()}

    def select(self, scan_filter: ScanFilter | None = None) -> tuple[BundleFile, ...]:
        if scan_filter is None:
            return self.files
        return tuple(item for item in self.files if scan_filter.matches(item))

    @property
    def frameworks(self) -> tuple[BundleFile, ...]:
        return self.section_index[BundleSection.FRAMEWORKS]

    @property
    def resources(self) -> tuple[BundleFile, ...]:
        return self.section_index[BundleSection.RESOURCES]

    @property
    def statistics(self) -> BundleStatistics:
        section_counts = {
            section.value: len(self.section_index[section]) for section in BundleSection
        }
        section_sizes = {
            section.value: sum(item.size_bytes for item in self.section_index[section])
            for section in BundleSection
        }
        return BundleStatistics(
            file_count=len(self.files),
            directory_count=self.directory_count,
            total_size_bytes=sum(item.size_bytes for item in self.files),
            symlink_count=sum(item.is_symlink for item in self.files),
            macho_count=sum(item.is_macho for item in self.files),
            python_count=sum(
                item.extension.casefold() in {".py", ".pyc", ".pyo"} for item in self.files
            ),
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses,
            section_counts=section_counts,
            section_sizes=section_sizes,
        )
