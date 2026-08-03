from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

from zerorod_analysis import __all__ as public_api
from zerorod_analysis.build_metadata import runtime_trace_version
from zerorod_analysis.runtime.schema import TRACE_ENABLE_ENV, TRACE_RAW_PATH_ENV

ROOT = Path(__file__).parents[1]


def test_runtime_core_has_no_desktop_or_qt_dependency() -> None:
    for path in (ROOT / "src" / "zerorod_analysis" / "runtime").glob("*.py"):
        text = path.read_text()
        assert "PySide6" not in text
        assert "zerorodcad_desktop" not in text


def test_public_api_is_unchanged_and_compatibility_has_no_recorder() -> None:
    assert public_api == [
        "analyze_bundle",
        "calculate_bundle_health",
        "generate_action_plan",
        "generate_reports",
    ]
    compatibility = (ROOT / "tools" / "trace_runtime_imports.py").read_text()
    tree = ast.parse(compatibility)
    assert not any(isinstance(node, ast.ClassDef | ast.FunctionDef) for node in ast.walk(tree))
    assert "addaudithook" not in compatibility and "atexit" not in compatibility


def test_runtime_version_uses_central_build_id() -> None:
    assert runtime_trace_version() == "ZeroRodCAD Runtime Trace – Build 021-M1"


def test_runtime_hook_is_inert_without_opt_in(tmp_path) -> None:
    raw = tmp_path / "disabled.jsonl"
    environment = os.environ.copy()
    environment.pop(TRACE_ENABLE_ENV, None)
    environment[TRACE_RAW_PATH_ENV] = str(raw)
    subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "macos" / "runtime_hook.py")],
        check=True,
        env=environment,
    )
    assert not raw.exists()


def test_runtime_hook_keeps_frozen_qt_plugin_path_behavior(tmp_path) -> None:
    plugin_root = tmp_path / "PySide6" / "Qt" / "plugins"
    plugin_root.mkdir(parents=True)
    code = (
        "import os,runpy,sys;"
        "sys.frozen=True;"
        f"sys._MEIPASS={str(tmp_path)!r};"
        f"runpy.run_path({str(ROOT / 'packaging/macos/runtime_hook.py')!r});"
        "print(os.environ.get('QT_PLUGIN_PATH',''))"
    )
    environment = os.environ.copy()
    environment.pop(TRACE_ENABLE_ENV, None)
    environment.pop("QT_PLUGIN_PATH", None)
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.stdout.strip() == str(plugin_root)
