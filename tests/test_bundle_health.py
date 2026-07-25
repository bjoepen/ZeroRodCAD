from __future__ import annotations

from pathlib import Path

from tools.bundle_analyzer.deadlibs import (
    BundleHealthEvaluator,
    ConfidenceLevel,
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    UsageRecord,
)


def test_empty_analysis_has_perfect_health() -> None:
    health = BundleHealthEvaluator().evaluate(DeadLibraryAnalysisResult())
    assert health.score == 100
    assert health.grade == "excellent"


def test_unused_bundle_content_reduces_health() -> None:
    library = LibraryUnit(
        identifier="Unused.framework",
        paths=[Path("Unused.framework")],
        size_bytes=500,
        category=FindingCategory.FRAMEWORK,
    )
    result = DeadLibraryAnalysisResult(
        total_bundle_size_bytes=1000,
        findings=[
            DeadLibraryFinding(
                library=library,
                usage=UsageRecord(library.identifier),
                confidence=ConfidenceLevel.HIGH,
                category=FindingCategory.UNUSED,
                recommendation=Recommendation.SAFE_REMOVE,
            )
        ],
    )

    health = BundleHealthEvaluator().evaluate(result)
    assert health.score < 100
    assert health.deductions
