import ast
from pathlib import Path

from tools.bundle_analyzer.deadlibs import (
    DeadLibraryAnalysisResult,
    write_dead_library_reports,
)
from tools.bundle_analyzer.macho import DependencyGraph, write_macho_reports

from zerorod_analysis import __all__ as public_exports
from zerorod_analysis import generate_action_plan, generate_reports

DEAD_LIBRARY_FILES = {
    "bundle-size-analysis.md",
    "dead-libraries.json",
    "dead-libraries.md",
    "optimization-plan.md",
    "optimization-report.md",
}


def test_public_and_legacy_dead_library_writers_keep_filenames(tmp_path: Path) -> None:
    result = DeadLibraryAnalysisResult()
    public_paths = generate_reports(result, tmp_path / "public")
    legacy_paths = write_dead_library_reports(result, tmp_path / "legacy")

    assert {path.name for path in public_paths} == DEAD_LIBRARY_FILES
    assert {path.name for path in legacy_paths} == DEAD_LIBRARY_FILES
    plan_path = tmp_path / "public" / "optimization-plan.md"
    assert generate_action_plan(result) == plan_path.read_text()


def test_legacy_macho_writer_delegates_with_compatible_order(tmp_path: Path) -> None:
    graph = DependencyGraph(edges={}, external_dependencies={}, reverse_edges={})
    paths = write_macho_reports((), graph, tmp_path)

    assert tuple(path.name for path in paths) == (
        "macho-dependencies.json",
        "macho-dependencies.md",
        "macho-dependencies.dot",
        "macho-unresolved.md",
    )


def test_public_exports_remain_unchanged() -> None:
    assert set(public_exports) == {
        "analyze_bundle",
        "calculate_bundle_health",
        "generate_action_plan",
        "generate_reports",
    }


def test_report_package_has_no_gui_scanner_or_otool_imports() -> None:
    report_root = Path(__file__).parents[1] / "src" / "zerorod_analysis" / "report"
    forbidden = {"PySide6", "zerorodcad_desktop", "scanner", "scanner2", "subprocess"}
    for source_path in report_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(
            part in forbidden for module in modules for part in module.replace(".", " ").split()
        ), source_path


def test_analysis_pipeline_does_not_import_or_write_reports() -> None:
    pipeline_root = Path(__file__).parents[1] / "src" / "zerorod_analysis" / "pipeline"
    for source_path in pipeline_root.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert "ReportEngine" not in source
        assert "write_text" not in source
