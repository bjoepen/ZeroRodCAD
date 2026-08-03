"""Graphviz DOT projection of the existing dependency graph."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...pipeline import AnalysisResult
from ..models import RenderedReport, ReportFormat, ReportRequest


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@dataclass(frozen=True, slots=True)
class DotRenderer:
    name: str = "dot"
    format: ReportFormat = ReportFormat.DOT

    def render(self, result: AnalysisResult, request: ReportRequest) -> tuple[RenderedReport, ...]:
        if not request.include_macho or result.dependency_graph is None:
            return ()
        lines = ["digraph macho_dependencies {", "  rankdir=LR;"]
        for source, targets in sorted(result.dependency_graph.edges.items()):
            escaped_source = _escape(source)
            if not targets:
                lines.append(f'  "{escaped_source}";')
            for target in sorted(targets):
                lines.append(f'  "{escaped_source}" -> "{_escape(target)}";')
        lines.append("}")
        return (
            RenderedReport(
                Path("macho-dependencies.dot"),
                self.format,
                "\n".join(lines) + "\n",
                "text/vnd.graphviz",
                22,
            ),
        )
