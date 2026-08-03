"""Stable public entry points for bundle analysis."""

from __future__ import annotations

from pathlib import Path

from .advisor import BundleHealth, BundleHealthEvaluator
from .deadlibs import DeadLibraryAnalysisResult
from .pipeline import AnalysisPipeline, AnalysisResult, PipelineContext
from .report import ReportEngine, ReportFormat, ReportRequest
from .scanner import ScanFilter


def analyze_bundle(
    app_bundle: str | Path,
    *,
    cache_dir: str | Path = Path(".cache/bundle-analyzer"),
    use_cache: bool = True,
    scan_filter: ScanFilter | None = None,
) -> AnalysisResult:
    """Analyze a macOS application bundle without modifying it."""

    context = PipelineContext(
        bundle_path=Path(app_bundle),
        cache_dir=Path(cache_dir),
        use_cache=use_cache,
        scan_filter=scan_filter,
    )
    return AnalysisPipeline.default().run(context)


def generate_reports(
    analysis: DeadLibraryAnalysisResult,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    """Write the established dead-library reports for an analysis result."""

    request = ReportRequest(output_directory=Path(output_dir))
    return ReportEngine.default().generate(analysis, request)


def generate_action_plan(analysis: DeadLibraryAnalysisResult) -> str:
    """Return the established Markdown optimization plan."""

    request = ReportRequest(
        output_directory=Path("."),
        requested_formats=frozenset({ReportFormat.MARKDOWN}),
    )
    manifest = ReportEngine.default().render(analysis, request)
    return next(
        report.content
        for report in manifest.reports
        if report.relative_path.name == "optimization-plan.md"
    )


def calculate_bundle_health(analysis: DeadLibraryAnalysisResult) -> BundleHealth:
    """Calculate the established bundle-health score."""

    return BundleHealthEvaluator().evaluate(analysis)
