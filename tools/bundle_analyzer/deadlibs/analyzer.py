"""High-level dead-library analysis orchestration."""

from __future__ import annotations

from tools.bundle_analyzer.macho import DependencyGraph
from tools.bundle_analyzer.scanner2 import BundleDatabase

from .aggregate import aggregate_library_units
from .models import DeadLibraryAnalysisResult
from .resolver import DeadLibraryResolver, resolve_usage


class DeadLibraryAnalyzer:
    def analyze(
        self,
        database: BundleDatabase,
        graph: DependencyGraph,
    ) -> DeadLibraryAnalysisResult:
        units = aggregate_library_units(database)
        usage = resolve_usage(database, graph, units)
        return DeadLibraryResolver().resolve(
            units,
            usage,
            bundle_root=database.root,
            total_bundle_size_bytes=database.statistics.total_size_bytes,
        )
