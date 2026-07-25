from __future__ import annotations

from pathlib import Path

from tools.bundle_analyzer.deadlibs import (
    ConfidenceLevel,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    RecommendationAdvisor,
    Reference,
    ReferenceKind,
    UsageRecord,
)


def make_finding(
    recommendation: Recommendation,
    *,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    references: list[Reference] | None = None,
) -> DeadLibraryFinding:
    library = LibraryUnit(
        identifier="Contents/Frameworks/Demo.framework",
        paths=[Path("Contents/Frameworks/Demo.framework")],
        size_bytes=4096,
        category=FindingCategory.FRAMEWORK,
    )
    return DeadLibraryFinding(
        library=library,
        usage=UsageRecord(library.identifier, references=references or []),
        confidence=confidence,
        category=FindingCategory.UNUSED,
        recommendation=recommendation,
        reasons=["Base analysis reason."],
    )


def test_safe_remove_advice_is_actionable_and_low_risk() -> None:
    advice = RecommendationAdvisor().advise(make_finding(Recommendation.SAFE_REMOVE))

    assert advice.recommendation is Recommendation.SAFE_REMOVE
    assert advice.risk_score <= 20
    assert advice.risk_label == "very-low"
    assert any("copy" in action.casefold() for action in advice.actions)


def test_macho_reference_is_explained_and_high_risk() -> None:
    reference = Reference(
        source="Contents/MacOS/Demo",
        target="Demo.framework",
        kind=ReferenceKind.MACHO_DEPENDENCY,
    )
    advice = RecommendationAdvisor().advise(
        make_finding(Recommendation.KEEP, references=[reference])
    )

    assert advice.risk_score >= 66
    assert any("Mach-O dependency" in reason for reason in advice.reasons)
    assert advice.actions == ("Keep the library in the bundle.",)
