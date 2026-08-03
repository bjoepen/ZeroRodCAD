import ast
import subprocess
from pathlib import Path

from tools.bundle_analyzer.macho import DependencyGraph as LegacyDependencyGraph

import zerorod_analysis
from zerorod_analysis.macho import DependencyGraph


def test_final_build020_packages_and_public_api() -> None:
    root = Path(zerorod_analysis.__file__).parent
    assert (root / "pipeline" / "pipeline.py").is_file()
    assert (root / "report" / "engine.py").is_file()
    assert (root / "metrics.py").is_file()
    assert set(zerorod_analysis.__all__) == {
        "analyze_bundle",
        "calculate_bundle_health",
        "generate_action_plan",
        "generate_reports",
    }
    assert LegacyDependencyGraph is DependencyGraph


def test_final_analysis_core_has_no_gui_imports() -> None:
    root = Path(zerorod_analysis.__file__).parent
    forbidden = {"PySide6", "zerorodcad_desktop"}
    for source_path in root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(name in module for name in forbidden for module in modules)


def test_no_generated_benchmark_results_are_tracked() -> None:
    root = Path(__file__).parents[1]
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert not any(path.startswith(("build/benchmarks/", ".cache/")) for path in tracked)
