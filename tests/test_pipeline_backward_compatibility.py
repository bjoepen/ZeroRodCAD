import ast
from pathlib import Path

from tools.bundle_analyzer.deadlibs import DeadLibraryAnalysisResult as LegacyAnalysisResult
from tools.bundle_analyzer.macho import DependencyGraph as LegacyDependencyGraph
from tools.bundle_analyzer.scanner2 import Scanner as LegacyScanner

from zerorod_analysis import __all__ as public_exports
from zerorod_analysis import generate_reports
from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.macho import DependencyGraph
from zerorod_analysis.pipeline import AnalysisPipeline, AnalysisResult, PipelineContext
from zerorod_analysis.scanner import Scanner


def test_pipeline_preserves_legacy_runtime_types() -> None:
    assert AnalysisResult is DeadLibraryAnalysisResult
    assert LegacyAnalysisResult is DeadLibraryAnalysisResult
    assert LegacyDependencyGraph is DependencyGraph
    assert LegacyScanner is Scanner


def test_pipeline_types_are_not_public_top_level_exports() -> None:
    assert set(public_exports) == {
        "analyze_bundle",
        "calculate_bundle_health",
        "generate_action_plan",
        "generate_reports",
    }
    assert "AnalysisPipeline" not in public_exports
    assert "PipelineContext" not in public_exports


def test_empty_pipeline_result_remains_report_compatible(tmp_path: Path) -> None:
    result = DeadLibraryAnalysisResult(bundle_root=Path("Fixture.app"))
    context = PipelineContext(Path("Fixture.app"), dead_library_result=result)

    assert AnalysisPipeline(()).run(context) is result


def test_public_reports_keep_established_filenames(tmp_path: Path) -> None:
    paths = generate_reports(DeadLibraryAnalysisResult(), tmp_path)

    assert {path.name for path in paths} == {
        "bundle-size-analysis.md",
        "dead-libraries.json",
        "dead-libraries.md",
        "optimization-plan.md",
        "optimization-report.md",
    }


def test_pipeline_stages_do_not_import_report_renderers() -> None:
    stages_root = Path(__file__).parents[1] / "src" / "zerorod_analysis" / "pipeline" / "stages"
    for source_path in stages_root.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        assert all("report" not in module for module in imported_modules), source_path


def test_compatibility_modules_define_no_analysis_logic() -> None:
    compatibility_root = Path(__file__).parents[1] / "tools" / "bundle_analyzer"
    for source_path in compatibility_root.rglob("*.py"):
        if source_path.name == "cli.py":
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        ]
        assert not definitions, source_path
