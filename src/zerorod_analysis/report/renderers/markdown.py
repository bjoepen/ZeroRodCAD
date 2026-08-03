"""Markdown projections of existing analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...deadlibs.report import (
    bundle_size_markdown,
    dead_libraries_markdown,
    human_size,
    optimization_markdown,
    optimization_plan_markdown,
)
from ...pipeline import AnalysisResult
from ..models import RenderedReport, ReportFormat, ReportRequest


def _macho_dependencies(result: AnalysisResult) -> str:
    items = result.macho_binaries or ()
    graph = result.dependency_graph
    assert graph is not None
    lines = [
        "# Mach-O Dependency Report",
        "",
        f"- Mach-O binaries: **{len(items)}**",
        f"- Internal edges: **{sum(len(values) for values in graph.edges.values())}**",
        "- External or unresolved dependencies: "
        f"**{sum(len(values) for values in graph.external_dependencies.values())}**",
        "",
        "## Dependencies",
        "",
    ]
    for item in sorted(items, key=lambda value: value.relative_path.casefold()):
        lines.extend([f"### `{item.relative_path}`", ""])
        targets = graph.edges.get(item.relative_path, ())
        lines.extend(f"- `{target}`" for target in targets)
        if not targets:
            lines.append("- _No internal dependencies_ ")
        lines.append("")
    return "\n".join(lines)


def _macho_unresolved(result: AnalysisResult) -> str:
    graph = result.dependency_graph
    assert graph is not None
    lines = ["# Unresolved Mach-O Dependencies", ""]
    unresolved_found = False
    for source, dependencies in sorted(graph.external_dependencies.items()):
        if not dependencies:
            continue
        unresolved_found = True
        lines.extend([f"## `{source}`", ""])
        lines.extend(f"- `{dependency}`" for dependency in dependencies)
        lines.append("")
    if not unresolved_found:
        lines.extend(["_No unresolved dependencies._", ""])
    return "\n".join(lines)


def _scanner_markdown(result: AnalysisResult) -> str:
    assert result.database is not None
    database = result.database
    statistics = database.statistics
    lines = [
        "# Build 019.1a – Scanner 2.0 Report",
        "",
        f"- Bundle: `{database.root}`",
        f"- Dateien: **{statistics.file_count}**",
        f"- Verzeichnisse: **{statistics.directory_count}**",
        f"- Gesamtgröße: **{human_size(statistics.total_size_bytes)}**",
        f"- Symbolische Links: **{statistics.symlink_count}**",
        f"- Mach-O-Dateien: **{statistics.macho_count}**",
        f"- Python-Dateien: **{statistics.python_count}**",
        f"- Cache-Treffer: **{statistics.cache_hits}**",
        f"- Cache-Fehlschläge: **{statistics.cache_misses}**",
        "",
        "## Bundle-Bereiche",
        "",
        "| Bereich | Dateien | Größe |",
        "|---|---:|---:|",
    ]
    for section, count in statistics.section_counts.items():
        lines.append(f"| {section} | {count} | {human_size(statistics.section_sizes[section])} |")
    lines.extend(
        [
            "",
            "> Der Scanner arbeitet ausschließlich lesend. Das App-Bundle wurde nicht verändert.",
            "",
        ]
    )
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class MarkdownRenderer:
    name: str = "markdown"
    format: ReportFormat = ReportFormat.MARKDOWN

    def render(self, result: AnalysisResult, request: ReportRequest) -> tuple[RenderedReport, ...]:
        reports: list[RenderedReport] = []
        if request.include_dead_libraries:
            reports.extend(
                (
                    RenderedReport(
                        Path("dead-libraries.md"),
                        self.format,
                        dead_libraries_markdown(result),
                        "text/markdown",
                        11,
                    ),
                    RenderedReport(
                        Path("bundle-size-analysis.md"),
                        self.format,
                        bundle_size_markdown(result),
                        "text/markdown",
                        12,
                    ),
                    RenderedReport(
                        Path("optimization-report.md"),
                        self.format,
                        optimization_markdown(result),
                        "text/markdown",
                        13,
                    ),
                )
            )
            if request.include_optimization_plan:
                reports.append(
                    RenderedReport(
                        Path("optimization-plan.md"),
                        self.format,
                        optimization_plan_markdown(result),
                        "text/markdown",
                        14,
                    )
                )
        if request.include_macho and result.dependency_graph is not None:
            reports.extend(
                (
                    RenderedReport(
                        Path("macho-dependencies.md"),
                        self.format,
                        _macho_dependencies(result),
                        "text/markdown",
                        21,
                    ),
                    RenderedReport(
                        Path("macho-unresolved.md"),
                        self.format,
                        _macho_unresolved(result),
                        "text/markdown",
                        23,
                    ),
                )
            )
        if request.include_scanner and result.database is not None:
            reports.append(
                RenderedReport(
                    Path("scanner2-report.md"),
                    self.format,
                    _scanner_markdown(result),
                    "text/markdown",
                    30,
                )
            )
        return tuple(reports)
