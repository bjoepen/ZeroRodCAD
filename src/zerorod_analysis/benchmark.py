"""Reproducible developer benchmark orchestration."""

from __future__ import annotations

import platform
import statistics
import tempfile
from dataclasses import asdict
from pathlib import Path

from .api import analyze_bundle
from .build_metadata import BUILD_ID
from .metrics import (
    BENCHMARK_SCHEMA_ID,
    BenchmarkResult,
    BenchmarkStatistics,
)
from .report import ReportEngine, ReportRequest


def _statistics(values: list[float]) -> BenchmarkStatistics:
    return BenchmarkStatistics(
        median_seconds=statistics.median(values),
        minimum_seconds=min(values),
        maximum_seconds=max(values),
        mean_seconds=statistics.fmean(values),
    )


def benchmark_bundle(
    app_bundle: str | Path,
    *,
    iterations: int = 3,
    warmup: int = 1,
    use_cache: bool = True,
) -> BenchmarkResult:
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    if warmup < 0:
        raise ValueError("warmup must not be negative")

    analysis_durations: list[float] = []
    report_durations: list[float] = []
    with tempfile.TemporaryDirectory(prefix="zerorod-benchmark-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        cache_dir = temporary_root / "cache"
        for index in range(warmup + iterations):
            result = analyze_bundle(app_bundle, cache_dir=cache_dir, use_cache=use_cache)
            if result.analysis_metrics is None:
                raise RuntimeError("analysis pipeline did not provide metrics")
            report_dir = temporary_root / f"reports-{index}"
            _, report_metrics = ReportEngine.default().generate_with_metrics(
                result,
                ReportRequest(report_dir),
            )
            if index >= warmup:
                analysis_durations.append(result.analysis_metrics.total_duration_seconds)
                report_durations.append(report_metrics.total_duration_seconds)

    return BenchmarkResult(
        schema=BENCHMARK_SCHEMA_ID,
        build_id=BUILD_ID,
        python_version=platform.python_version(),
        platform=platform.platform(),
        iterations=iterations,
        warmup=warmup,
        use_cache=use_cache,
        analysis=_statistics(analysis_durations),
        reporting=_statistics(report_durations),
    )


def benchmark_payload(result: BenchmarkResult) -> dict[str, object]:
    return asdict(result)
