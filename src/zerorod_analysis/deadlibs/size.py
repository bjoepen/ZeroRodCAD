"""Size aggregation helpers for dead-library findings."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import (
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    LibraryUnit,
    Recommendation,
)


@dataclass(frozen=True, slots=True)
class SizeSummary:
    total_library_bytes: int
    potential_savings_bytes: int
    finding_count: int
    safe_remove_count: int

    @property
    def total_bytes(self) -> int:
        return self.total_library_bytes

    @property
    def largest_library_id(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class SizeAnalysis:
    entries: tuple[tuple[str, int], ...]
    total_bytes: int


def summarize_sizes(
    source: Iterable[LibraryUnit] | DeadLibraryAnalysisResult,
) -> SizeSummary:
    if isinstance(source, DeadLibraryAnalysisResult):
        findings = source.findings
        return SizeSummary(
            total_library_bytes=sum(item.library.size_bytes for item in findings),
            potential_savings_bytes=sum(
                item.library.size_bytes
                for item in findings
                if item.recommendation is Recommendation.SAFE_REMOVE
            ),
            finding_count=len(findings),
            safe_remove_count=sum(
                item.recommendation is Recommendation.SAFE_REMOVE for item in findings
            ),
        )

    units = list(source)
    return SizeSummary(
        total_library_bytes=sum(unit.size_bytes for unit in units),
        potential_savings_bytes=0,
        finding_count=len(units),
        safe_remove_count=0,
    )


def compute_savings(findings: Iterable[DeadLibraryFinding]) -> SizeAnalysis:
    entries = sorted(
        (
            (finding.library.identifier, finding.library.size_bytes)
            for finding in findings
            if finding.recommendation is Recommendation.SAFE_REMOVE
        ),
        key=lambda item: (-item[1], item[0].casefold()),
    )
    return SizeAnalysis(entries=tuple(entries), total_bytes=sum(size for _, size in entries))
