"""Renderer contract for the unified report engine."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..pipeline import AnalysisResult
from .models import RenderedReport, ReportFormat, ReportRequest


@runtime_checkable
class ReportRenderer(Protocol):
    name: str
    format: ReportFormat

    def render(
        self,
        result: AnalysisResult,
        request: ReportRequest,
    ) -> tuple[RenderedReport, ...]: ...
