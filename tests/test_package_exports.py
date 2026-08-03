import ast
from pathlib import Path

import zerorod_analysis

EXPECTED_EXPORTS = {
    "analyze_bundle",
    "generate_reports",
    "generate_action_plan",
    "calculate_bundle_health",
}


def test_package_exports_only_approved_public_api() -> None:
    assert set(zerorod_analysis.__all__) == EXPECTED_EXPORTS
    namespace: dict[str, object] = {}
    exec("from zerorod_analysis import *", namespace)
    assert {name for name in namespace if name != "__builtins__"} == EXPECTED_EXPORTS


def test_analysis_core_has_no_gui_or_pyside_imports() -> None:
    package_root = Path(zerorod_analysis.__file__).parent
    forbidden = {"PySide6", "zerorodcad_desktop"}
    for source_path in package_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import | ast.ImportFrom)
            for alias in (node.names if isinstance(node, ast.Import) else [])
        }
        imports.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert not imports & forbidden, source_path


def test_internal_import_graph_is_acyclic() -> None:
    package_root = Path(zerorod_analysis.__file__).parent
    graph: dict[str, set[str]] = {}
    for source_path in package_root.rglob("*.py"):
        module = ".".join(source_path.relative_to(package_root).with_suffix("").parts)
        graph[module] = set()
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                base = module.split(".")[: -node.level]
                target = ".".join([*base, *(node.module or "").split(".")]).strip(".")
                if target in graph or (package_root / Path(*target.split("."))).exists():
                    graph[module].add(target)

    def visit(module: str, path: set[str]) -> None:
        assert module not in path, f"cyclic import involving {module}"
        for dependency in graph.get(module, set()):
            visit(dependency, path | {module})

    for module in graph:
        visit(module, set())
