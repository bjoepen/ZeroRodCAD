"""Data-only models for report requests and rendered output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

REPORT_SCHEMA_ID = "zerorod-analysis/report/v1"


class ReportFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"
    DOT = "dot"


@dataclass(frozen=True, slots=True)
class ReportRequest:
    output_directory: Path
    requested_formats: frozenset[ReportFormat] = frozenset(ReportFormat)
    include_scanner: bool = False
    include_macho: bool = False
    include_dead_libraries: bool = True
    include_optimization_plan: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_directory", Path(self.output_directory))


@dataclass(frozen=True, slots=True)
class RenderedReport:
    relative_path: Path
    format: ReportFormat
    content: str
    media_type: str
    order: int


@dataclass(frozen=True, slots=True)
class ReportWarning:
    message: str


@dataclass(frozen=True, slots=True)
class ReportManifest:
    schema: str
    reports: tuple[RenderedReport, ...]
