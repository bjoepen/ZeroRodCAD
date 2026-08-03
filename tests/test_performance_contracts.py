import ast
from pathlib import Path

from zerorod_analysis.metrics import (
    BENCHMARK_SCHEMA_ID,
    PipelineMetrics,
    ReportMetrics,
    StageTiming,
)


def test_metrics_are_data_only_and_non_negative_contracts() -> None:
    pipeline = PipelineMetrics(0.0, (StageTiming("scanner", 0.0),))
    report = ReportMetrics(0.0, (), 0)

    assert pipeline.total_duration_seconds >= 0
    assert report.total_duration_seconds >= 0
    assert BENCHMARK_SCHEMA_ID == "zerorod-analysis/benchmark/v1"


def test_metrics_and_benchmark_modules_have_no_gui_imports() -> None:
    root = Path(__file__).parents[1] / "src" / "zerorod_analysis"
    forbidden = {"PySide6", "zerorodcad_desktop"}
    for relative in ("metrics.py", "benchmark.py"):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not any(name in module for name in forbidden for module in modules)
