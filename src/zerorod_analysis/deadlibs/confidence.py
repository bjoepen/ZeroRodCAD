"""Confidence and recommendation rules for dead-library findings."""

from __future__ import annotations

from .models import (
    ConfidenceLevel,
    FindingCategory,
    Recommendation,
    UsageRecord,
)


def classify_confidence(score: float) -> ConfidenceLevel:
    if not 0.0 <= score <= 1.0:
        raise ValueError("confidence score must be between 0.0 and 1.0")
    if score >= 0.8:
        return ConfidenceLevel.HIGH
    if score >= 0.4:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def assess_usage(
    record: UsageRecord,
    category: FindingCategory,
) -> tuple[ConfidenceLevel, Recommendation, list[str]]:
    if record.dynamic_hints or record.unresolved_hints:
        reasons = ["Dynamic or unresolved loading evidence requires manual review."]
        return ConfidenceLevel.LOW, Recommendation.REVIEW, reasons

    if record.static_references:
        reasons = ["At least one explicit static usage reference was found."]
        return ConfidenceLevel.HIGH, Recommendation.KEEP, reasons

    if category is FindingCategory.DUPLICATE:
        return (
            ConfidenceLevel.HIGH,
            Recommendation.SAFE_REMOVE,
            ["The file is a redundant copy of a canonical library path."],
        )

    cautious_categories = {
        FindingCategory.RESOURCE,
        FindingCategory.PYTHON_PACKAGE,
    }
    if category in cautious_categories:
        return (
            ConfidenceLevel.MEDIUM,
            Recommendation.REVIEW,
            ["No direct reference was found, but detection is incomplete for this category."],
        )

    return (
        ConfidenceLevel.HIGH,
        Recommendation.SAFE_REMOVE,
        [
            "No Mach-O dependency was found.",
            "No Python import or plugin reference was found.",
            "No dynamic loading hint was found.",
        ],
    )
