"""Shared state passed through one analysis-pipeline run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..advisor import Advice, BundleHealth
from ..deadlibs import DeadLibraryAnalysisResult
from ..macho import DependencyGraph, MachOBinary
from ..scanner import BundleDatabase, ScanFilter


@dataclass(slots=True)
class PipelineContext:
    """Data-only transport for configuration and intermediate results."""

    bundle_path: Path
    cache_dir: Path = Path(".cache/bundle-analyzer")
    use_cache: bool = True
    scan_filter: ScanFilter | None = None
    output_directory: Path | None = None
    database: BundleDatabase | None = None
    macho_binaries: tuple[MachOBinary, ...] | None = None
    dependency_graph: DependencyGraph | None = None
    dead_library_result: DeadLibraryAnalysisResult | None = None
    advisor_results: tuple[Advice, ...] | None = None
    bundle_health: BundleHealth | None = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.bundle_path = Path(self.bundle_path)
        self.cache_dir = Path(self.cache_dir)
        if self.output_directory is not None:
            self.output_directory = Path(self.output_directory)
