"""Initial resolver for deriving dead-library findings from usage evidence."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .confidence import classify_confidence
from .models import (
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    UsageRecord,
)


class DeadLibraryResolver:
    """Create deterministic findings for already aggregated library units.

    Milestone M1 intentionally accepts prepared ``UsageRecord`` objects. Later
    milestones will populate those records from Mach-O, Python imports, plugin
    manifests, and dynamic-load evidence.
    """

    def resolve(
        self,
        units: Iterable[LibraryUnit],
        usage_by_library: Mapping[str, UsageRecord] | None = None,
    ) -> DeadLibraryAnalysisResult:
        usage_records = usage_by_library or {}
        findings: list[DeadLibraryFinding] = []

        for unit in sorted(units, key=lambda item: item.identifier.casefold()):
            usage = usage_records.get(unit.identifier, UsageRecord(unit.identifier))
            findings.append(self._finding_for(unit, usage))

        return DeadLibraryAnalysisResult(findings=findings)

    @staticmethod
    def _finding_for(unit: LibraryUnit, usage: UsageRecord) -> DeadLibraryFinding:
        if usage.references:
            return DeadLibraryFinding(
                library=unit,
                usage=usage,
                confidence=classify_confidence(1.0),
                category=FindingCategory.REFERENCED,
                recommendation=Recommendation.KEEP,
                reasons=["At least one explicit usage reference was found."],
            )

        if usage.unresolved_hints:
            return DeadLibraryFinding(
                library=unit,
                usage=usage,
                confidence=classify_confidence(0.5),
                category=FindingCategory.POSSIBLY_UNUSED,
                recommendation=Recommendation.REVIEW,
                reasons=["No direct reference was found, but unresolved usage hints remain."],
            )

        return DeadLibraryFinding(
            library=unit,
            usage=usage,
            confidence=classify_confidence(0.9),
            category=FindingCategory.UNUSED,
            recommendation=Recommendation.SAFE_REMOVE,
            reasons=["No usage references or unresolved hints were found."],
        )
