"""Non-destructive temporary smoke test for the M3 report engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

from zerorod_analysis import generate_reports
from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult

EXPECTED = {
    "bundle-size-analysis.md",
    "dead-libraries.json",
    "dead-libraries.md",
    "optimization-plan.md",
    "optimization-report.md",
}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="zerorod-report-smoke-") as temporary_directory:
        output_directory = Path(temporary_directory) / "reports"
        paths = generate_reports(DeadLibraryAnalysisResult(), output_directory)
        names = {path.name for path in paths}
        if names != EXPECTED or not all(path.is_file() for path in paths):
            raise RuntimeError(f"unexpected report smoke-test output: {sorted(names)}")


if __name__ == "__main__":
    main()
