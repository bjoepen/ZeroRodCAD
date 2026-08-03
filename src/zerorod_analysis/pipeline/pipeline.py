"""Ordered orchestration of the existing analysis components."""

from __future__ import annotations

from dataclasses import dataclass

from ..deadlibs import DeadLibraryAnalysisResult
from ..exceptions import MissingStageResultError, PipelineError, StageExecutionError
from .context import PipelineContext
from .contracts import AnalysisStage
from .stages import AdvisorStage, DeadLibraryStage, MachOStage, ScannerStage

AnalysisResult = DeadLibraryAnalysisResult


@dataclass(frozen=True, slots=True)
class AnalysisPipeline:
    """Execute a fixed, inspectable sequence of analysis stages."""

    stages: tuple[AnalysisStage, ...]

    @classmethod
    def default(cls) -> AnalysisPipeline:
        """Build the standard M2 pipeline in its required order."""

        return cls((ScannerStage(), MachOStage(), DeadLibraryStage(), AdvisorStage()))

    @property
    def stage_names(self) -> tuple[str, ...]:
        return tuple(stage.name for stage in self.stages)

    def run(self, context: PipelineContext) -> AnalysisResult:
        for stage in self.stages:
            try:
                stage.run(context)
            except PipelineError:
                raise
            except Exception as exc:
                raise StageExecutionError(stage.name, context.bundle_path, exc) from exc

        if context.dead_library_result is None:
            final_stage = self.stage_names[-1] if self.stages else "pipeline"
            raise MissingStageResultError(final_stage, context.bundle_path, "dead_library_result")
        return context.dead_library_result
