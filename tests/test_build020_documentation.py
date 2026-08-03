import os
from pathlib import Path


def test_consolidated_build020_documentation_exists() -> None:
    root = Path(__file__).parents[1]
    required = (
        "docs/BUILD-020-OVERVIEW.md",
        "docs/ARCHITECTURE-BUILD020.md",
        "docs/PUBLIC-API-BUILD020.md",
        "docs/MODULE-OVERVIEW.md",
        "docs/MIGRATION-BUILD020.md",
        "docs/RELEASE-NOTES-BUILD020.md",
        "docs/PERFORMANCE-BUILD020-M4.md",
        "docs/performance/BUILD020-M4-BASELINE.json",
        "docs/adr/ADR-020-002-ANALYSIS-PIPELINE.md",
        "docs/adr/ADR-020-003-UNIFIED-REPORT-ENGINE.md",
        "docs/adr/ADR-020-004-PERFORMANCE-METRICS-AND-BENCHMARKS.md",
    )
    assert all((root / relative).is_file() for relative in required)


def test_m4_validation_script_is_executable() -> None:
    script = Path(__file__).parents[1] / "scripts" / "validate-build020-m4.sh"
    assert script.is_file()
    assert os.access(script, os.X_OK)
