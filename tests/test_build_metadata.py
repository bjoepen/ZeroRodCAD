import ast
import subprocess
import sys
from pathlib import Path

from zerorod_analysis.build_metadata import BUILD_ID, benchmark_version, scanner_version


def test_scanner_and_benchmark_share_build_metadata() -> None:
    assert BUILD_ID == "020-M4"
    assert BUILD_ID in scanner_version()
    assert BUILD_ID in benchmark_version()


def test_cli_and_module_report_same_scanner_version() -> None:
    root = Path(__file__).parents[1]
    commands = (
        [sys.executable, "tools/scan_bundle.py", "--version"],
        [sys.executable, "-m", "tools.scan_bundle", "--version"],
    )
    outputs = [
        subprocess.run(command, cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        for command in commands
    ]
    assert outputs == [scanner_version(), scanner_version()]


def test_current_build_literal_has_one_productive_definition() -> None:
    root = Path(__file__).parents[1]
    matches = []
    for base in (root / "src", root / "tools"):
        for source_path in base.rglob("*.py"):
            if '"020-M4"' in source_path.read_text(encoding="utf-8"):
                matches.append(source_path.relative_to(root).as_posix())
    assert matches == ["src/zerorod_analysis/build_metadata.py"]


def test_productive_tools_import_central_metadata() -> None:
    root = Path(__file__).parents[1]
    for relative in ("tools/scan_bundle.py", "tools/benchmark_analysis.py"):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert "zerorod_analysis.build_metadata" in modules
