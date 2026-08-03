"""Typed contract implemented by every pipeline stage."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .context import PipelineContext


@runtime_checkable
class AnalysisStage(Protocol):
    """A named operation that updates one shared pipeline context."""

    name: str

    def run(self, context: PipelineContext) -> None:
        """Populate only the results owned by this stage."""
        ...
