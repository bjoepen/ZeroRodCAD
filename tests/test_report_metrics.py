from pathlib import Path

from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.report import ReportEngine
from zerorod_analysis.report.models import ReportFormat, ReportRequest


def test_report_metrics_count_requested_renderers_once(tmp_path: Path) -> None:
    request = ReportRequest(
        tmp_path,
        requested_formats=frozenset({ReportFormat.JSON, ReportFormat.MARKDOWN}),
    )
    paths, metrics = ReportEngine.default().generate_with_metrics(
        DeadLibraryAnalysisResult(), request
    )

    assert metrics.renderer_invocation_counts == {"json": 1, "markdown": 1}
    assert "dot" not in metrics.renderer_invocation_counts
    assert metrics.rendered_file_count == len(paths) == 5
    assert all(timing.duration_seconds >= 0 for timing in metrics.renderer_timings)
    assert metrics.total_duration_seconds >= sum(
        timing.duration_seconds for timing in metrics.renderer_timings
    )
