"""Data-only per-run performance and diagnostic models."""

from __future__ import annotations

from dataclasses import dataclass

BENCHMARK_SCHEMA_ID = "zerorod-analysis/benchmark/v1"


@dataclass(frozen=True, slots=True)
class StageTiming:
    stage_name: str
    duration_seconds: float
    invocation_count: int = 1


@dataclass(frozen=True, slots=True)
class PipelineMetrics:
    total_duration_seconds: float
    stage_timings: tuple[StageTiming, ...]

    def invocation_count(self, stage_name: str) -> int:
        return sum(
            timing.invocation_count
            for timing in self.stage_timings
            if timing.stage_name == stage_name
        )

    @property
    def scanner_invocations(self) -> int:
        return self.invocation_count("scanner")

    @property
    def macho_analyzer_invocations(self) -> int:
        return self.invocation_count("macho")

    @property
    def dependency_graph_builds(self) -> int:
        return self.invocation_count("macho")

    @property
    def dead_library_analyzer_invocations(self) -> int:
        return self.invocation_count("dead-libraries")

    @property
    def advisor_invocations(self) -> int:
        return self.invocation_count("advisor")


@dataclass(frozen=True, slots=True)
class RendererTiming:
    renderer_name: str
    duration_seconds: float
    invocation_count: int = 1


@dataclass(frozen=True, slots=True)
class ReportMetrics:
    total_duration_seconds: float
    renderer_timings: tuple[RendererTiming, ...]
    rendered_file_count: int

    @property
    def renderer_invocation_counts(self) -> dict[str, int]:
        return {timing.renderer_name: timing.invocation_count for timing in self.renderer_timings}


@dataclass(frozen=True, slots=True)
class BenchmarkStatistics:
    median_seconds: float
    minimum_seconds: float
    maximum_seconds: float
    mean_seconds: float


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    schema: str
    build_id: str
    python_version: str
    platform: str
    iterations: int
    warmup: int
    use_cache: bool
    analysis: BenchmarkStatistics
    reporting: BenchmarkStatistics
