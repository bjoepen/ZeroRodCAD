from __future__ import annotations

from pathlib import Path

from .database import BundleDatabase


def human_size(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def write_scanner_reports(
    database: BundleDatabase,
    output_dir: Path,
) -> tuple[Path, Path]:
    from ..deadlibs import DeadLibraryAnalysisResult
    from ..report import ReportEngine, ReportRequest

    result = DeadLibraryAnalysisResult(
        bundle_root=database.root,
        total_bundle_size_bytes=database.statistics.total_size_bytes,
        database=database,
    )
    request = ReportRequest(
        output_directory=output_dir,
        include_scanner=True,
        include_dead_libraries=False,
        include_optimization_plan=False,
    )
    paths = ReportEngine.default().generate(result, request)
    return paths  # type: ignore[return-value]
