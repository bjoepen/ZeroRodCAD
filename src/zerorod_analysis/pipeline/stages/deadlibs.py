"""Dead-library stage."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...deadlibs import DeadLibraryAnalyzer
from ...exceptions import MissingStageResultError
from ..context import PipelineContext


@dataclass(slots=True)
class DeadLibraryStage:
    """Consume existing scanner and graph results without rebuilding either."""

    name: str = "dead-libraries"
    analyzer: DeadLibraryAnalyzer = field(default_factory=DeadLibraryAnalyzer)

    def run(self, context: PipelineContext) -> None:
        if context.database is None:
            raise MissingStageResultError(self.name, context.bundle_path, "database")
        if context.dependency_graph is None:
            raise MissingStageResultError(self.name, context.bundle_path, "dependency_graph")
        context.dead_library_result = self.analyzer.analyze(
            context.database,
            context.dependency_graph,
        )
