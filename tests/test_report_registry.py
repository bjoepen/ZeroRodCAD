from dataclasses import dataclass

import pytest

from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.report.contracts import ReportRenderer
from zerorod_analysis.report.models import RenderedReport, ReportFormat, ReportRequest
from zerorod_analysis.report.registry import RendererRegistry


@dataclass
class StubRenderer:
    name: str
    format: ReportFormat

    def render(
        self, result: DeadLibraryAnalysisResult, request: ReportRequest
    ) -> tuple[RenderedReport, ...]:
        return ()


def test_renderer_satisfies_contract() -> None:
    assert isinstance(StubRenderer("json", ReportFormat.JSON), ReportRenderer)


def test_registry_rejects_duplicate_names_and_formats() -> None:
    with pytest.raises(ValueError, match="names"):
        RendererRegistry(
            (
                StubRenderer("same", ReportFormat.JSON),
                StubRenderer("same", ReportFormat.DOT),
            )
        )
    with pytest.raises(ValueError, match="formats"):
        RendererRegistry(
            (
                StubRenderer("first", ReportFormat.JSON),
                StubRenderer("second", ReportFormat.JSON),
            )
        )


def test_registry_selects_only_requested_format() -> None:
    json_renderer = StubRenderer("json", ReportFormat.JSON)
    dot_renderer = StubRenderer("dot", ReportFormat.DOT)
    registry = RendererRegistry((json_renderer, dot_renderer))

    assert registry.select(frozenset({ReportFormat.DOT})) == (dot_renderer,)
