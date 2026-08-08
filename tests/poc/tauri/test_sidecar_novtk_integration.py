"""Integration test: the sidecar run as a real subprocess against the
TE-001.1-patched, VTK-free `.venv-novtk-poc` interpreter (TE-002 sections
14-15). Skipped when that environment doesn't exist — it's TE-001-family
PoC infrastructure, never required for the normal test suite / CI.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
POC_VENV_PYTHON = REPO_ROOT / ".venv-novtk-poc" / "bin" / "python"

pytestmark = pytest.mark.skipif(
    not POC_VENV_PYTHON.exists(),
    reason="TE-001 .venv-novtk-poc not present; run scripts/validate-te001-novtk.sh to create it",
)


def _run_sidecar(request_json: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(POC_VENV_PYTHON), "-m", "tools.poc.tauri.sidecar"],
        input=request_json,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _preview_request() -> str:
    return json.dumps(
        {
            "schema": "zerorod-sidecar/v1",
            "request_id": "novtk-1",
            "command": "preview",
            "parameters": {},
        }
    )


def test_sidecar_exits_zero_with_real_mesh_and_no_vtk_installed():
    result = _run_sidecar(_preview_request())
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"stdout must be exactly one JSON line, got: {result.stdout!r}"
    response = json.loads(lines[0])
    assert response["ok"] is True
    assert len(response["result"]["meshes"]) > 0


def test_sidecar_stdout_is_not_corrupted_by_stderr():
    result = _run_sidecar(_preview_request())
    # The single stdout line must itself be valid JSON, proving stderr
    # (if any) never leaked into stdout.
    json.loads(result.stdout.strip())


def test_sys_modules_contain_no_vtk_or_pyside6():
    probe = """
import sys, json
sys.path.insert(0, ".")
from tools.poc.tauri.sidecar.main import main
main()
vtk_hits = [m for m in sys.modules if m.split(".", 1)[0].lower() in ("vtk", "vtkmodules")]
pyside_hits = [m for m in sys.modules if m.split(".", 1)[0].lower() == "pyside6"]
print(json.dumps({"vtk_hits": vtk_hits, "pyside_hits": pyside_hits}), file=sys.stderr)
"""
    result = subprocess.run(
        [str(POC_VENV_PYTHON), "-c", probe],
        input=_preview_request(),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    report = json.loads(result.stderr.strip().splitlines()[-1])
    assert report["vtk_hits"] == []
    assert report["pyside_hits"] == []


def test_package_audit_novtk_venv():
    show_ocp = subprocess.run(
        [str(POC_VENV_PYTHON), "-m", "pip", "show", "cadquery-ocp"],
        capture_output=True,
        text=True,
    )
    show_novtk = subprocess.run(
        [str(POC_VENV_PYTHON), "-m", "pip", "show", "cadquery-ocp-novtk"],
        capture_output=True,
        text=True,
    )
    show_vtk = subprocess.run(
        [str(POC_VENV_PYTHON), "-m", "pip", "show", "vtk"],
        capture_output=True,
        text=True,
    )
    assert show_ocp.returncode != 0, "cadquery-ocp must not be installed"
    assert show_novtk.returncode == 0, "cadquery-ocp-novtk must be installed"
    assert show_vtk.returncode != 0, "vtk must not be installed"
