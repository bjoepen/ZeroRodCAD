"""Size aggregation for dead-library findings."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DeadLibraryAnalysisResult, Recommendation


@dataclass(frozen=True, slots=True)
class SizeSummary:
    """Aggregated size metrics for an analysis result."""

    total_library_bytes: int
    potential_savings_bytes: int
    finding_count: int
    safe_remove_count: int


def summarize_sizes(result: DeadLibraryAnalysisResult) -> SizeSummary:
    """Return deterministic bundle-size metrics for *result*."""

    return SizeSummary(
        total_library_bytes=sum(finding.library.size_bytes for finding in result.findings),
        potential_savings_bytes=result.potential_savings_bytes,
        finding_count=len(result.findings),
        safe_remove_count=sum(
            finding.recommendation is Recommendation.SAFE_REMOVE for finding in result.findings
        ),
    )
