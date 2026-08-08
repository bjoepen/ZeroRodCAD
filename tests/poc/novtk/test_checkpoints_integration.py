"""Integration test for the TE-001 checkpoint runner against the real
``.venv-novtk-poc`` environment (section 9-16, 28).

Skipped when that environment doesn't exist (it is a TE-001-only artifact,
never required for the normal test suite / CI). When present, this exercises
the actual novtk install against the actual ZeroRodCAD engine — no mocks, no
dummy geometry, per the TE-001 mandate.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
POC_VENV_PYTHON = REPO_ROOT / ".venv-novtk-poc" / "bin" / "python"

pytestmark = pytest.mark.skipif(
    not POC_VENV_PYTHON.exists(),
    reason="TE-001 .venv-novtk-poc not present; run scripts/validate-te001-novtk.sh to create it",
)


def _run_checkpoints() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "checkpoints.json"
        raw_trace_path = Path(tmp) / "raw-trace.jsonl"
        subprocess.run(
            [
                str(POC_VENV_PYTHON),
                str(REPO_ROOT / "tools" / "poc" / "novtk" / "run_checkpoints.py"),
                "--report",
                str(report_path),
                "--raw-trace",
                str(raw_trace_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        return json.loads(report_path.read_text(encoding="utf-8"))


def test_checkpoint_report_has_all_six_checkpoints_in_order():
    report = _run_checkpoints()
    names = [c["name"] for c in report["checkpoints"]]
    assert names == ["import", "geometry", "tessellate", "preview-mesh", "stl", "step"]


def test_no_checkpoint_ever_shows_vtk_in_sys_modules():
    report = _run_checkpoints()
    for checkpoint in report["checkpoints"]:
        assert checkpoint["sys_modules_vtk_hits"] == [], checkpoint


def test_report_is_deterministic_in_shape_across_runs():
    first = _run_checkpoints()
    second = _run_checkpoints()
    first_names_statuses = [(c["name"], c["status"]) for c in first["checkpoints"]]
    second_names_statuses = [(c["name"], c["status"]) for c in second["checkpoints"]]
    assert first_names_statuses == second_names_statuses
    assert first["overall"] == second["overall"]


def test_current_empirical_result_is_import_blocked_by_upstream_vtkmodules_coupling():
    """Documents the actual TE-001 finding as a regression guard: if this ever
    starts passing, it means upstream cadquery stopped eagerly importing
    vtkmodules and Gate A's premise should be re-evaluated end to end."""
    report = _run_checkpoints()
    import_checkpoint = next(c for c in report["checkpoints"] if c["name"] == "import")
    if import_checkpoint["status"] == "fail":
        assert "vtkmodules" in import_checkpoint["detail"]
    else:
        pytest.skip(
            "cadquery no longer eagerly imports vtkmodules at import time; "
            "re-run the full TE-001 evidence gathering, this changes the Gate A outcome"
        )


def test_ivtk_boundary_probe_runs_clean():
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "ivtk.json"
        result = subprocess.run(
            [
                str(POC_VENV_PYTHON),
                str(REPO_ROOT / "tools" / "poc" / "novtk" / "ivtk_boundary.py"),
                "--report",
                str(report_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["overall"] == "acceptable"
        assert result.returncode == 0


def test_no_stray_export_tempdirs_leak(tmp_path):
    # export_project uses a TemporaryDirectory context manager inside run_checkpoints.py;
    # since the current empirical result never reaches that checkpoint (import fails
    # first), this just guards that the checkpoint runner itself doesn't leave anything
    # behind in the system tempdir.
    import tempfile as _tempfile

    before = {p.name for p in Path(_tempfile.gettempdir()).glob("te001-export-*")}
    _run_checkpoints()
    after = {p.name for p in Path(_tempfile.gettempdir()).glob("te001-export-*")}
    assert after - before == set()
