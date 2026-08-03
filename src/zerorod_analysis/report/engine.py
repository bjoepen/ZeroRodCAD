"""Unified rendering and atomic report persistence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from ..metrics import RendererTiming, ReportMetrics
from ..pipeline import AnalysisResult
from .models import REPORT_SCHEMA_ID, ReportManifest, ReportRequest
from .paths import atomic_write_text, resolve_report_path
from .registry import RendererRegistry
from .renderers import DotRenderer, JsonRenderer, MarkdownRenderer


@dataclass(frozen=True, slots=True)
class ReportEngine:
    registry: RendererRegistry

    @classmethod
    def default(cls) -> ReportEngine:
        return cls(RendererRegistry((JsonRenderer(), MarkdownRenderer(), DotRenderer())))

    def render(self, result: AnalysisResult, request: ReportRequest) -> ReportManifest:
        manifest, _ = self.render_with_metrics(result, request)
        return manifest

    def render_with_metrics(
        self, result: AnalysisResult, request: ReportRequest
    ) -> tuple[ReportManifest, ReportMetrics]:
        started = perf_counter()
        reports = []
        timings = []
        for renderer in self.registry.select(request.requested_formats):
            renderer_started = perf_counter()
            reports.extend(renderer.render(result, request))
            timings.append(RendererTiming(renderer.name, perf_counter() - renderer_started))
        paths = [report.relative_path for report in reports]
        if len(paths) != len(set(paths)):
            raise ValueError("renderers produced colliding report paths")
        for relative_path in paths:
            resolve_report_path(request.output_directory, relative_path)
        ordered = tuple(sorted(reports, key=lambda item: item.order))
        metrics = ReportMetrics(perf_counter() - started, tuple(timings), len(ordered))
        return ReportManifest(REPORT_SCHEMA_ID, ordered), metrics

    def generate(self, result: AnalysisResult, request: ReportRequest) -> tuple[Path, ...]:
        paths, _ = self.generate_with_metrics(result, request)
        return paths

    def generate_with_metrics(
        self, result: AnalysisResult, request: ReportRequest
    ) -> tuple[tuple[Path, ...], ReportMetrics]:
        started = perf_counter()
        if result.bundle_root is not None:
            bundle_root = result.bundle_root.resolve()
            output_root = request.output_directory.resolve()
            if output_root == bundle_root or bundle_root in output_root.parents:
                raise ValueError("report output directory must not be inside the analyzed bundle")
        manifest, metrics = self.render_with_metrics(result, request)
        paths = tuple(
            resolve_report_path(request.output_directory, report.relative_path)
            for report in manifest.reports
        )
        for path, report in zip(paths, manifest.reports, strict=True):
            atomic_write_text(path, report.content)
        return paths, ReportMetrics(
            perf_counter() - started,
            metrics.renderer_timings,
            metrics.rendered_file_count,
        )
