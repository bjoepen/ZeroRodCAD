"""Scanner stage."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...scanner import Scanner
from ..context import PipelineContext


@dataclass(slots=True)
class ScannerStage:
    """Run the existing bundle scanner exactly once."""

    name: str = "scanner"
    scanner: Scanner = field(default_factory=Scanner)

    def run(self, context: PipelineContext) -> None:
        context.database = self.scanner.scan(
            context.bundle_path,
            cache_dir=context.cache_dir,
            use_cache=context.use_cache,
            scan_filter=context.scan_filter,
        )
