"""Tests for zerorod_sidecar.main's persistent transport loop (Build 022 M2).

Unit-level tests exercise `run_persistent()` directly via monkeypatched
stdin/stdout (fast, no process spawn). A separate real-subprocess test class
confirms the actual sidecar CLI behaves identically end to end, against the
same TE-001.1-patched, VTK-free interpreter the research evaluations used
(`.venv-novtk-poc`) — no new environment invented for this.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from zerorod_sidecar.main import run_persistent
from zerorod_sidecar.protocol import SIDECAR_SCHEMA

REPO_ROOT = Path(__file__).resolve().parents[1]
POC_VENV_PYTHON = REPO_ROOT / ".venv-novtk-poc" / "bin" / "python"


def _req(request_id: str, command: str, parameters: dict | None = None) -> str:
    return (
        json.dumps(
            {
                "schema": SIDECAR_SCHEMA,
                "request_id": request_id,
                "command": command,
                "parameters": parameters or {},
            }
        )
        + "\n"
    )


def _run(monkeypatch, lines: str) -> list[dict]:
    monkeypatch.setattr("sys.stdin", io.StringIO(lines))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    exit_code = run_persistent()
    assert exit_code == 0
    return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]


def test_multiple_sequential_requests_get_matching_responses(monkeypatch):
    lines = _req("a", "ping") + _req("b", "status") + _req("c", "preview") + _req("d", "shutdown")
    responses = _run(monkeypatch, lines)
    assert [r["request_id"] for r in responses] == ["a", "b", "c", "d"]
    assert all(r["ok"] for r in responses)


def test_request_id_is_echoed_exactly_per_line(monkeypatch):
    lines = _req("first-id", "ping") + _req("second-id", "ping") + _req("stop", "shutdown")
    responses = _run(monkeypatch, lines)
    assert responses[0]["request_id"] == "first-id"
    assert responses[1]["request_id"] == "second-id"


def test_malformed_json_line_does_not_stop_the_loop(monkeypatch):
    lines = "not json\n" + _req("after", "ping") + _req("stop", "shutdown")
    responses = _run(monkeypatch, lines)
    assert responses[0]["ok"] is False
    assert responses[0]["error"]["code"] == "invalid_json"
    assert responses[1]["ok"] is True
    assert responses[1]["request_id"] == "after"


def test_request_after_a_prior_error_still_gets_a_clean_response(monkeypatch):
    lines = _req("bad", "unknown-cmd") + _req("good", "ping") + _req("stop", "shutdown")
    responses = _run(monkeypatch, lines)
    assert responses[0]["ok"] is False
    assert responses[1]["ok"] is True
    assert responses[1]["result"]["status"] == "ok"


def test_shutdown_ends_the_loop_and_ignores_lines_after_it(monkeypatch):
    lines = _req("a", "ping") + _req("stop", "shutdown") + _req("never-processed", "ping")
    responses = _run(monkeypatch, lines)
    assert [r["request_id"] for r in responses] == ["a", "stop"]


def test_eof_without_shutdown_ends_the_loop_cleanly(monkeypatch):
    lines = _req("a", "ping")  # no shutdown, no trailing newline issues
    responses = _run(monkeypatch, lines)
    assert len(responses) == 1
    assert responses[0]["request_id"] == "a"


def test_blank_lines_between_requests_are_skipped(monkeypatch):
    lines = _req("a", "ping") + "\n\n" + _req("stop", "shutdown")
    responses = _run(monkeypatch, lines)
    assert [r["request_id"] for r in responses] == ["a", "stop"]


def test_invalid_parameters_request_does_not_kill_the_persistent_loop(monkeypatch):
    """Build 023 M1: an invalid zerorod-parameters/v1 request must not
    corrupt the stdout protocol or end the persistent loop — the next valid
    request on the same (in this unit test: simulated) process must still
    succeed."""
    bad_params = {
        "schema": "zerorod-parameters/v1",
        "values": {"body_width": -1.0},
    }
    lines = (
        _req("good-1", "preview")
        + _req("bad", "preview", bad_params)
        + _req("good-2", "preview")
        + _req("stop", "shutdown")
    )
    responses = _run(monkeypatch, lines)
    assert [r["request_id"] for r in responses] == ["good-1", "bad", "good-2", "stop"]
    assert responses[0]["ok"] is True
    assert responses[1]["ok"] is False
    assert responses[1]["error"]["code"] == "invalid_parameters_domain"
    assert responses[2]["ok"] is True
    assert responses[3]["ok"] is True


class TestRealPersistentSubprocess:
    """Same behaviors, but through the actual sidecar CLI and a real
    subprocess against the TE-001.1-patched, VTK-free interpreter."""

    pytestmark = pytest.mark.skipif(
        not POC_VENV_PYTHON.exists(),
        reason="TE-001 .venv-novtk-poc not present; run scripts/validate-te001-novtk.sh first",
    )

    def _run_subprocess(self, input_text: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(POC_VENV_PYTHON), "-m", "zerorod_sidecar", "--persistent"],
            input=input_text,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_real_subprocess_handles_multiple_requests_and_shutdown(self):
        lines = _req("ping-1", "ping") + _req("preview-1", "preview") + _req("bye", "shutdown")
        result = self._run_subprocess(lines)
        assert result.returncode == 0
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        assert len(responses) == 3
        assert responses[1]["result"]["meshes"][0]["name"] in {"body", "rod"}

    def test_real_subprocess_stdout_has_no_corruption(self):
        lines = _req("a", "ping") + _req("stop", "shutdown")
        result = self._run_subprocess(lines)
        for line in result.stdout.splitlines():
            if line.strip():
                json.loads(line)  # must not raise

    def test_real_subprocess_valid_invalid_valid_parameter_sequence(self):
        """Build 023 M1: proves process stability against the real bundled
        interpreter, not just the monkeypatched unit test above — an invalid
        zerorod-parameters/v1 request must not crash the real subprocess or
        corrupt its stdout, and the next valid request must still succeed."""
        bad_params = {"schema": "zerorod-parameters/v1", "values": {"rod_diameter": -1.0}}
        lines = (
            _req("good-1", "preview")
            + _req("bad", "preview", bad_params)
            + _req("good-2", "preview")
            + _req("bye", "shutdown")
        )
        result = self._run_subprocess(lines)
        assert result.returncode == 0
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        assert len(responses) == 4
        assert responses[0]["ok"] is True
        assert responses[1]["ok"] is False
        assert responses[1]["error"]["code"] == "invalid_parameters_domain"
        assert responses[2]["ok"] is True
        assert responses[3]["ok"] is True

    def test_real_subprocess_no_vtk_or_pyside6(self):
        probe = """
import sys, json
from zerorod_sidecar.main import main
main(["--persistent"])
vtk_hits = [m for m in sys.modules if m.split(".", 1)[0].lower() in ("vtk", "vtkmodules")]
pyside_hits = [m for m in sys.modules if m.split(".", 1)[0].lower() == "pyside6"]
print(json.dumps({"vtk_hits": vtk_hits, "pyside_hits": pyside_hits}), file=sys.stderr)
"""
        lines = _req("a", "preview") + _req("stop", "shutdown")
        result = subprocess.run(
            [str(POC_VENV_PYTHON), "-c", probe],
            input=lines,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        report = json.loads(result.stderr.strip().splitlines()[-1])
        assert report["vtk_hits"] == []
        assert report["pyside_hits"] == []
