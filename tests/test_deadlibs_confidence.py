from tools.bundle_analyzer.deadlibs import (
    ConfidenceLevel,
    FindingCategory,
    Recommendation,
    Reference,
    ReferenceKind,
    UsageRecord,
    assess_usage,
)


def test_dynamic_hint_has_priority_over_static_reference() -> None:
    record = UsageRecord(
        "QtPdf",
        references=[
            Reference("app", "QtPdf", ReferenceKind.MACHO_DEPENDENCY),
            Reference("app.py", "QtPdf", ReferenceKind.DYNAMIC_LOAD_HINT),
        ],
    )

    confidence, recommendation, _ = assess_usage(record, FindingCategory.FRAMEWORK)

    assert confidence is ConfidenceLevel.LOW
    assert recommendation is Recommendation.REVIEW


def test_unreferenced_python_package_requires_review() -> None:
    confidence, recommendation, _ = assess_usage(
        UsageRecord("optional_package"),
        FindingCategory.PYTHON_PACKAGE,
    )

    assert confidence is ConfidenceLevel.MEDIUM
    assert recommendation is Recommendation.REVIEW
