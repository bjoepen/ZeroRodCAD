from __future__ import annotations

import json
from pathlib import Path

from tools.bundle_analyzer.deadlibs import (
    ConfidenceLevel,
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    Reference,
    ReferenceKind,
    UsageRecord,
    result_payload,
    write_dead_library_reports,
)


def make_result(tmp_path: Path) -> DeadLibraryAnalysisResult:
    removable = LibraryUnit(
        identifier="Contents/Frameworks/Unused.framework",
        paths=[Path("Contents/Frameworks/Unused.framework")],
        size_bytes=4096,
        category=FindingCategory.FRAMEWORK,
    )
    kept = LibraryUnit(
        identifier="Contents/Frameworks/Used.framework",
        paths=[Path("Contents/Frameworks/Used.framework")],
        size_bytes=2048,
        category=FindingCategory.FRAMEWORK,
    )
    return DeadLibraryAnalysisResult(
        bundle_root=tmp_path / "Demo.app",
        total_bundle_size_bytes=16384,
        findings=[
            DeadLibraryFinding(
                library=removable,
                usage=UsageRecord(removable.identifier),
                confidence=ConfidenceLevel.HIGH,
                category=FindingCategory.UNUSED,
                recommendation=Recommendation.SAFE_REMOVE,
                reasons=["No static reference was found."],
            ),
            DeadLibraryFinding(
                library=kept,
                usage=UsageRecord(
                    kept.identifier,
                    references=[
                        Reference(
                            source="Contents/MacOS/Demo",
                            target=kept.identifier,
                            kind=ReferenceKind.MACHO_DEPENDENCY,
                            detail="LC_LOAD_DYLIB",
                        )
                    ],
                ),
                confidence=ConfidenceLevel.HIGH,
                category=FindingCategory.REFERENCED,
                recommendation=Recommendation.KEEP,
                reasons=["Static dependency found."],
            ),
        ],
    )


def test_result_payload_is_canonical_and_complete(tmp_path: Path) -> None:
    payload = result_payload(make_result(tmp_path))

    assert payload["schema_version"] == 2
    assert payload["summary"]["finding_count"] == 2
    assert payload["summary"]["potential_savings_bytes"] == 4096
    assert payload["summary"]["safe_remove_count"] == 1
    assert payload["bundle_health"]["score"] <= 100
    assert payload["findings"][0]["risk_score"] <= 20
    assert payload["findings"][1]["references"][0]["kind"] == "macho-dependency"


def test_report_writer_creates_json_and_markdown_projections(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    paths = write_dead_library_reports(make_result(tmp_path), output_dir)

    assert {path.name for path in paths} == {
        "dead-libraries.json",
        "dead-libraries.md",
        "bundle-size-analysis.md",
        "optimization-report.md",
        "optimization-plan.md",
    }
    payload = json.loads((output_dir / "dead-libraries.json").read_text(encoding="utf-8"))
    assert payload["summary"]["potential_savings_bytes"] == 4096
    assert "SAFE REMOVE" in (output_dir / "dead-libraries.md").read_text(encoding="utf-8")
    assert "Unused.framework" in (output_dir / "bundle-size-analysis.md").read_text(
        encoding="utf-8"
    )
    assert "KEEP" in (output_dir / "optimization-report.md").read_text(encoding="utf-8")
    assert "Priorisierte Maßnahmen" in (output_dir / "optimization-plan.md").read_text(
        encoding="utf-8"
    )
