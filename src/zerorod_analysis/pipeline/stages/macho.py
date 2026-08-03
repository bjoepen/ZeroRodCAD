"""Mach-O stage."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...exceptions import MissingStageResultError
from ...macho import MachOAnalyzer, build_dependency_graph
from ..context import PipelineContext


@dataclass(slots=True)
class MachOStage:
    """Analyze the scanner database and build one dependency graph."""

    name: str = "macho"
    analyzer: MachOAnalyzer = field(default_factory=MachOAnalyzer)

    def run(self, context: PipelineContext) -> None:
        if context.database is None:
            raise MissingStageResultError(self.name, context.bundle_path, "database")
        context.macho_binaries = self.analyzer.analyze(context.database)
        context.dependency_graph = build_dependency_graph(
            context.macho_binaries,
            bundle_root=context.database.root,
        )
