from dataclasses import dataclass, field
from pathlib import Path

import pytest

from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.report import ReportEngine
from zerorod_analysis.report.models import RenderedReport, ReportFormat, ReportRequest
from zerorod_analysis.report.registry import RendererRegistry


@dataclass
class CountingRenderer:
    name: str
    format: ReportFormat
    calls: list[str] = field(default_factory=list)
    relative_path: Path = Path("report.txt")

    def render(
        self, result: DeadLibraryAnalysisResult, request: ReportRequest
    ) -> tuple[RenderedReport, ...]:
        self.calls.append(self.name)
        return (RenderedReport(self.relative_path, self.format, self.name, "text/plain", 1),)


def test_default_engine_registers_three_standard_renderers() -> None:
    engine = ReportEngine.default()
    assert tuple(renderer.name for renderer in engine.registry.renderers) == (
        "json",
        "markdown",
        "dot",
    )


def test_requested_renderer_runs_once_and_other_renderer_does_not(tmp_path: Path) -> None:
    json_renderer = CountingRenderer("json", ReportFormat.JSON)
    dot_renderer = CountingRenderer("dot", ReportFormat.DOT, relative_path=Path("graph.dot"))
    engine = ReportEngine(RendererRegistry((json_renderer, dot_renderer)))
    request = ReportRequest(tmp_path, requested_formats=frozenset({ReportFormat.JSON}))

    engine.generate(DeadLibraryAnalysisResult(), request)

    assert json_renderer.calls == ["json"]
    assert dot_renderer.calls == []


def test_engine_rejects_renderer_path_collisions(tmp_path: Path) -> None:
    first = CountingRenderer("json", ReportFormat.JSON)
    second = CountingRenderer("dot", ReportFormat.DOT)
    engine = ReportEngine(RendererRegistry((first, second)))

    with pytest.raises(ValueError, match="colliding"):
        engine.generate(DeadLibraryAnalysisResult(), ReportRequest(tmp_path))


def test_engine_never_writes_inside_analyzed_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "Unsafe.app"
    result = DeadLibraryAnalysisResult(bundle_root=bundle)

    with pytest.raises(ValueError, match="analyzed bundle"):
        ReportEngine.default().generate(result, ReportRequest(bundle / "Contents" / "Reports"))


def test_generate_reports_delegates_to_engine(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    from zerorod_analysis import api

    observed: list[ReportRequest] = []

    class RecordingEngine:
        def generate(self, result, request):  # type: ignore[no-untyped-def]
            observed.append(request)
            return (tmp_path / "sentinel",)

    monkeypatch.setattr(api.ReportEngine, "default", lambda: RecordingEngine())

    assert api.generate_reports(DeadLibraryAnalysisResult(), tmp_path) == (tmp_path / "sentinel",)
    assert len(observed) == 1
