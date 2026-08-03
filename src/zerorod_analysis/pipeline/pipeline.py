"""Ordered orchestration of the existing analysis components."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from ..deadlibs import DeadLibraryAnalysisResult
from ..exceptions import MissingStageResultError, PipelineError, StageExecutionError
from ..metrics import PipelineMetrics, StageTiming
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
        pipeline_started = perf_counter()
        timings: list[StageTiming] = []
        for stage in self.stages:
            stage_started = perf_counter()
            try:
                stage.run(context)
            except PipelineError as exc:
                timings.append(StageTiming(stage.name, perf_counter() - stage_started))
                exc.metrics = PipelineMetrics(perf_counter() - pipeline_started, tuple(timings))
                raise
            except Exception as exc:
                timings.append(StageTiming(stage.name, perf_counter() - stage_started))
                metrics = PipelineMetrics(perf_counter() - pipeline_started, tuple(timings))
                raise StageExecutionError(
                    stage.name, context.bundle_path, exc, metrics=metrics
                ) from exc
            timings.append(StageTiming(stage.name, perf_counter() - stage_started))

        if context.dead_library_result is None:
            final_stage = self.stage_names[-1] if self.stages else "pipeline"
            raise MissingStageResultError(final_stage, context.bundle_path, "dead_library_result")
        context.dead_library_result.database = context.database
        context.dead_library_result.macho_binaries = context.macho_binaries
        context.dead_library_result.dependency_graph = context.dependency_graph
        context.dead_library_result.advisor_results = context.advisor_results
        context.dead_library_result.bundle_health = context.bundle_health
        context.dead_library_result.analysis_metrics = PipelineMetrics(
            perf_counter() - pipeline_started,
            tuple(timings),
        )
        return context.dead_library_result
