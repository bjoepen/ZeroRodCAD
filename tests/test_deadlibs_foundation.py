from pathlib import Path

import pytest
from tools.bundle_analyzer.deadlibs import (
    ConfidenceLevel,
    DeadLibraryResolver,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    Reference,
    ReferenceKind,
    UsageRecord,
    classify_confidence,
    summarize_sizes,
)


def test_classify_confidence_boundaries() -> None:
    assert classify_confidence(0.0) is ConfidenceLevel.LOW
    assert classify_confidence(0.4) is ConfidenceLevel.MEDIUM
    assert classify_confidence(0.8) is ConfidenceLevel.HIGH
    assert classify_confidence(1.0) is ConfidenceLevel.HIGH


def test_classify_confidence_rejects_out_of_range_scores() -> None:
    with pytest.raises(ValueError):
        classify_confidence(-0.01)
    with pytest.raises(ValueError):
        classify_confidence(1.01)


def test_library_unit_normalizes_paths_and_validates_size() -> None:
    unit = LibraryUnit("QtCore", paths=["Frameworks/QtCore"], size_bytes=1024)

    assert unit.paths == [Path("Frameworks/QtCore")]

    with pytest.raises(ValueError):
        LibraryUnit("QtCore", size_bytes=-1)


def test_resolver_marks_unreferenced_unit_safe_to_remove() -> None:
    result = DeadLibraryResolver().resolve([LibraryUnit("Unused", size_bytes=400)])

    finding = result.findings[0]
    assert finding.category is FindingCategory.UNUSED
    assert finding.recommendation is Recommendation.SAFE_REMOVE
    assert result.potential_savings_bytes == 400


def test_resolver_keeps_referenced_unit() -> None:
    usage = UsageRecord(
        "Used",
        references=[
            Reference(
                source="MacOS/ZeroRodCAD",
                target="Frameworks/Used.dylib",
                kind=ReferenceKind.MACHO,
            )
        ],
    )

    result = DeadLibraryResolver().resolve(
        [LibraryUnit("Used", size_bytes=300)],
        {"Used": usage},
    )

    finding = result.findings[0]
    assert finding.category is FindingCategory.REFERENCED
    assert finding.recommendation is Recommendation.KEEP
    assert result.potential_savings_bytes == 0


def test_resolver_marks_unresolved_hints_for_review() -> None:
    usage = UsageRecord("Dynamic", unresolved_hints=["dlopen candidate"])

    result = DeadLibraryResolver().resolve(
        [LibraryUnit("Dynamic", size_bytes=250)],
        {"Dynamic": usage},
    )

    assert result.findings[0].recommendation is Recommendation.REVIEW


def test_size_summary_uses_only_safe_remove_findings() -> None:
    units = [
        LibraryUnit("Unused", size_bytes=400),
        LibraryUnit("Used", size_bytes=600),
    ]
    used = UsageRecord(
        "Used",
        references=[Reference("app", "Used", ReferenceKind.MACHO)],
    )
    result = DeadLibraryResolver().resolve(units, {"Used": used})

    summary = summarize_sizes(result)

    assert summary.total_library_bytes == 1000
    assert summary.potential_savings_bytes == 400
    assert summary.finding_count == 2
    assert summary.safe_remove_count == 1
