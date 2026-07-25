from __future__ import annotations

from pathlib import Path

import pytest
from tools.bundle_analyzer.deadlibs import (
    ConfidenceLevel,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    Reference,
    ReferenceKind,
    RiskEvaluator,
    UsageRecord,
)


def finding(*, dynamic: bool = False) -> DeadLibraryFinding:
    library = LibraryUnit(
        identifier="libdemo.dylib",
        paths=[Path("Contents/Frameworks/libdemo.dylib")],
        category=FindingCategory.DYLIB,
    )
    references = []
    if dynamic:
        references.append(
            Reference("loader.py", library.identifier, ReferenceKind.DYNAMIC_LOAD_HINT)
        )
    return DeadLibraryFinding(
        library=library,
        usage=UsageRecord(library.identifier, references=references),
        confidence=ConfidenceLevel.LOW if dynamic else ConfidenceLevel.HIGH,
        category=FindingCategory.POSSIBLY_UNUSED if dynamic else FindingCategory.UNUSED,
        recommendation=Recommendation.REVIEW if dynamic else Recommendation.SAFE_REMOVE,
    )


def test_dynamic_loading_increases_risk_score() -> None:
    evaluator = RiskEvaluator()
    assert evaluator.evaluate(finding(dynamic=True)) > evaluator.evaluate(finding())


def test_risk_labels_validate_bounds() -> None:
    evaluator = RiskEvaluator()
    assert evaluator.label(0) == "very-low"
    assert evaluator.label(100) == "critical"
    with pytest.raises(ValueError):
        evaluator.label(101)
