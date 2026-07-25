from __future__ import annotations

from pathlib import Path

from tools.bundle_analyzer.deadlibs import (
    ConfidenceLevel,
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    UsageRecord,
    optimization_plan_markdown,
)


def test_action_plan_prioritizes_safe_remove_before_keep() -> None:
    unused = LibraryUnit("Unused.framework", [Path("Unused.framework")], 500)
    used = LibraryUnit("Used.framework", [Path("Used.framework")], 1000)
    result = DeadLibraryAnalysisResult(
        total_bundle_size_bytes=2000,
        findings=[
            DeadLibraryFinding(
                used,
                UsageRecord(used.identifier),
                ConfidenceLevel.HIGH,
                FindingCategory.REFERENCED,
                Recommendation.KEEP,
                ["Required."],
            ),
            DeadLibraryFinding(
                unused,
                UsageRecord(unused.identifier),
                ConfidenceLevel.HIGH,
                FindingCategory.UNUSED,
                Recommendation.SAFE_REMOVE,
                ["Unused."],
            ),
        ],
    )

    report = optimization_plan_markdown(result)
    assert report.index("SAFE REMOVE") < report.index("KEEP")
    assert "Risk Score" in report
    assert "Bundle Health" in report
