"""Unified rendering and atomic report persistence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
        reports = tuple(
            report
            for renderer in self.registry.select(request.requested_formats)
            for report in renderer.render(result, request)
        )
        paths = [report.relative_path for report in reports]
        if len(paths) != len(set(paths)):
            raise ValueError("renderers produced colliding report paths")
        for relative_path in paths:
            resolve_report_path(request.output_directory, relative_path)
        return ReportManifest(REPORT_SCHEMA_ID, tuple(sorted(reports, key=lambda item: item.order)))

    def generate(self, result: AnalysisResult, request: ReportRequest) -> tuple[Path, ...]:
        if result.bundle_root is not None:
            bundle_root = result.bundle_root.resolve()
            output_root = request.output_directory.resolve()
            if output_root == bundle_root or bundle_root in output_root.parents:
                raise ValueError("report output directory must not be inside the analyzed bundle")
        manifest = self.render(result, request)
        paths = tuple(
            resolve_report_path(request.output_directory, report.relative_path)
            for report in manifest.reports
        )
        for path, report in zip(paths, manifest.reports, strict=True):
            atomic_write_text(path, report.content)
        return paths
