from pathlib import Path

import pytest

from zerorod_analysis import analyze_bundle
from zerorod_analysis.exceptions import StageExecutionError
from zerorod_analysis.pipeline import AnalysisPipeline, PipelineContext


def make_bundle(tmp_path: Path) -> Path:
    executable = tmp_path / "Metrics.app" / "Contents" / "MacOS" / "metrics"
    executable.parent.mkdir(parents=True)
    executable.write_text("not Mach-O", encoding="utf-8")
    return executable.parents[2]


def test_pipeline_metrics_record_each_stage_once(tmp_path: Path) -> None:
    result = analyze_bundle(make_bundle(tmp_path), cache_dir=tmp_path / "cache", use_cache=False)
    metrics = result.analysis_metrics

    assert metrics is not None
    assert tuple(timing.stage_name for timing in metrics.stage_timings) == (
        "scanner",
        "macho",
        "dead-libraries",
        "advisor",
    )
    assert all(timing.invocation_count == 1 for timing in metrics.stage_timings)
    assert all(timing.duration_seconds >= 0 for timing in metrics.stage_timings)
    assert metrics.total_duration_seconds >= sum(
        timing.duration_seconds for timing in metrics.stage_timings
    )
    assert metrics.scanner_invocations == 1
    assert metrics.macho_analyzer_invocations == 1
    assert metrics.dependency_graph_builds == 1
    assert metrics.dead_library_analyzer_invocations == 1
    assert metrics.advisor_invocations == 1


def test_failed_stage_exposes_partial_metrics() -> None:
    class BrokenStage:
        name = "broken"

        def run(self, context: PipelineContext) -> None:
            raise RuntimeError("failure")

    with pytest.raises(StageExecutionError) as error:
        AnalysisPipeline((BrokenStage(),)).run(PipelineContext(Path("Broken.app")))

    assert error.value.metrics is not None
    assert error.value.metrics.stage_timings[0].stage_name == "broken"
    assert error.value.metrics.stage_timings[0].invocation_count == 1
