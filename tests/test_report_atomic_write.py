from pathlib import Path

import pytest

from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.report import ReportEngine
from zerorod_analysis.report.models import RenderedReport, ReportFormat, ReportRequest
from zerorod_analysis.report.paths import atomic_write_text, resolve_report_path
from zerorod_analysis.report.registry import RendererRegistry


def test_atomic_write_replaces_complete_file(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    target.write_text("old", encoding="utf-8")

    atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "new"
    assert list(tmp_path.iterdir()) == [target]


def test_failed_rendering_leaves_no_partial_file(tmp_path: Path) -> None:
    class BrokenRenderer:
        name = "broken"
        format = ReportFormat.JSON

        def render(self, result, request):  # type: ignore[no-untyped-def]
            raise RuntimeError("render failed")

    engine = ReportEngine(RendererRegistry((BrokenRenderer(),)))
    with pytest.raises(RuntimeError, match="render failed"):
        engine.generate(DeadLibraryAnalysisResult(), ReportRequest(tmp_path))

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("relative_path", [Path("../escape.md"), Path("/absolute.md")])
def test_path_traversal_is_rejected(tmp_path: Path, relative_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_report_path(tmp_path, relative_path)


def test_renderer_path_traversal_is_rejected_before_writing(tmp_path: Path) -> None:
    class UnsafeRenderer:
        name = "unsafe"
        format = ReportFormat.JSON

        def render(self, result, request):  # type: ignore[no-untyped-def]
            return (
                RenderedReport(Path("../escape.json"), self.format, "{}", "application/json", 1),
            )

    engine = ReportEngine(RendererRegistry((UnsafeRenderer(),)))
    with pytest.raises(ValueError, match="escapes"):
        engine.generate(DeadLibraryAnalysisResult(), ReportRequest(tmp_path))

    assert not (tmp_path.parent / "escape.json").exists()
