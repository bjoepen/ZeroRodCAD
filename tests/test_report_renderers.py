import json
from pathlib import Path

from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.deadlibs.advisor import BundleHealth, RecommendationAdvisor
from zerorod_analysis.macho import DependencyGraph, MachOBinary
from zerorod_analysis.report.models import ReportRequest
from zerorod_analysis.report.renderers import DotRenderer, JsonRenderer, MarkdownRenderer


def make_result() -> DeadLibraryAnalysisResult:
    return DeadLibraryAnalysisResult(
        macho_binaries=(MachOBinary('Contents/MacOS/A"B', None, ()),),
        dependency_graph=DependencyGraph(
            edges={'Contents/MacOS/A"B': ("Contents/Frameworks/Z",)},
            external_dependencies={'Contents/MacOS/A"B': ()},
            reverse_edges={"Contents/Frameworks/Z": ('Contents/MacOS/A"B',)},
        ),
    )


def test_json_markdown_and_dot_are_deterministic(tmp_path: Path) -> None:
    result = make_result()
    request = ReportRequest(tmp_path, include_macho=True)
    renderers = (JsonRenderer(), MarkdownRenderer(), DotRenderer())

    for renderer in renderers:
        assert renderer.render(result, request) == renderer.render(result, request)

    json_reports = JsonRenderer().render(result, request)
    for report in json_reports:
        json.loads(report.content)
    dot = DotRenderer().render(result, request)[0].content
    assert '"Contents/MacOS/A\\"B"' in dot


def test_renderers_only_read_precomputed_result(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    import subprocess

    def reject_otool(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("otool called")

    monkeypatch.setattr(subprocess, "run", reject_otool)
    request = ReportRequest(tmp_path, include_macho=True)

    for renderer in (JsonRenderer(), MarkdownRenderer(), DotRenderer()):
        renderer.render(make_result(), request)


def test_renderer_uses_precomputed_advisor_and_health(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    result = make_result()
    result.advisor_results = ()
    result.bundle_health = BundleHealth(100, "excellent", ())

    def reject_advice(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("advisor recalculated")

    monkeypatch.setattr(RecommendationAdvisor, "advise", reject_advice)
    request = ReportRequest(tmp_path, include_macho=True)

    JsonRenderer().render(result, request)
    MarkdownRenderer().render(result, request)
