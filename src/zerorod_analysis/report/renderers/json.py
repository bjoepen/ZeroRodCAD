"""JSON projections of existing analysis results."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ...deadlibs.report import result_payload
from ...pipeline import AnalysisResult
from ..models import RenderedReport, ReportFormat, ReportRequest


def _json(value: object, *, trailing_newline: bool) -> str:
    content = json.dumps(value, ensure_ascii=False, indent=2)
    return content + "\n" if trailing_newline else content


@dataclass(frozen=True, slots=True)
class JsonRenderer:
    name: str = "json"
    format: ReportFormat = ReportFormat.JSON

    def render(self, result: AnalysisResult, request: ReportRequest) -> tuple[RenderedReport, ...]:
        reports: list[RenderedReport] = []
        if request.include_dead_libraries:
            reports.append(
                RenderedReport(
                    Path("dead-libraries.json"),
                    self.format,
                    _json(result_payload(result), trailing_newline=True),
                    "application/json",
                    10,
                )
            )
        if request.include_macho and result.dependency_graph is not None:
            binaries = result.macho_binaries or ()
            graph = result.dependency_graph
            payload = {
                "binaries": [
                    {
                        "relative_path": item.relative_path,
                        "macho_id": item.macho_id,
                        "raw_dependencies": list(item.raw_dependencies),
                        "resolved_dependencies": list(graph.edges.get(item.relative_path, ())),
                        "external_dependencies": list(
                            graph.external_dependencies.get(item.relative_path, ())
                        ),
                    }
                    for item in binaries
                ],
                "reverse_edges": {
                    key: list(values) for key, values in sorted(graph.reverse_edges.items())
                },
            }
            reports.append(
                RenderedReport(
                    Path("macho-dependencies.json"),
                    self.format,
                    _json(payload, trailing_newline=True),
                    "application/json",
                    20,
                )
            )
        if request.include_scanner and result.database is not None:
            database = result.database
            payload = {
                "bundle": str(database.root),
                "statistics": asdict(database.statistics),
                "files": [
                    {
                        "relative_path": item.relative_path,
                        "filename": item.filename,
                        "extension": item.extension,
                        "size_bytes": item.size_bytes,
                        "sha256": item.sha256,
                        "modified_ns": item.modified_ns,
                        "inode": item.inode,
                        "device": item.device,
                        "is_symlink": item.is_symlink,
                        "symlink_target": item.symlink_target,
                        "section": item.section.value,
                        "is_macho": item.is_macho,
                        "architecture": list(item.architecture),
                    }
                    for item in database.files
                ],
            }
            reports.append(
                RenderedReport(
                    Path("scanner2-inventory.json"),
                    self.format,
                    _json(payload, trailing_newline=False),
                    "application/json",
                    31,
                )
            )
        return tuple(reports)
