"""Exceptions raised by the analysis package."""

from __future__ import annotations

from pathlib import Path


class AnalysisError(Exception):
    """Base exception for bundle-analysis failures."""


class PipelineError(AnalysisError):
    """Base exception for pipeline orchestration failures."""

    metrics: object | None = None


class MissingStageResultError(PipelineError):
    """Raised when a stage's required predecessor result is absent."""

    def __init__(self, stage_name: str, bundle_path: Path, result_name: str) -> None:
        self.stage_name = stage_name
        self.bundle_path = bundle_path
        self.result_name = result_name
        super().__init__(
            f"Stage '{stage_name}' cannot analyze '{bundle_path}': "
            f"required result '{result_name}' is missing"
        )


class StageExecutionError(PipelineError):
    """Add stage and bundle context to an underlying execution failure."""

    def __init__(
        self,
        stage_name: str,
        bundle_path: Path,
        cause: Exception,
        metrics: object | None = None,
    ) -> None:
        self.stage_name = stage_name
        self.bundle_path = bundle_path
        self.cause = cause
        self.metrics = metrics
        super().__init__(f"Stage '{stage_name}' failed for '{bundle_path}': {cause}")
