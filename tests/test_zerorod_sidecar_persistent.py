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

    def test_real_subprocess_preview_export_preview_export_shutdown_sequence(self, tmp_path):
        """Build 024 M1 §42/§32: the real bundled-interpreter proof that
        export works end to end through the actual persistent process loop,
        and that preview keeps working after an export (and after a second
        export with different parameters) in the same process — no
        restart, no protocol corruption, no orphan."""
        default_dir = tmp_path / "default"
        alt_dir = tmp_path / "alt"
        alt_params = {"schema": "zerorod-parameters/v1", "values": {"body_width": 60.0}}
        export_default_params = {"output_directory": str(default_dir)}
        export_alt_params = {"output_directory": str(alt_dir), "parameters": alt_params}

        lines = (
            _req("preview-1", "preview")
            + _req("export-1", "export", export_default_params)
            + _req("preview-2", "preview")
            + _req("export-2", "export", export_alt_params)
            + _req("preview-3", "preview")
            + _req("bye", "shutdown")
        )
        result = self._run_subprocess(lines)
        assert result.returncode == 0
        responses = {
            r["request_id"]: r
            for r in (json.loads(line) for line in result.stdout.splitlines() if line.strip())
        }
        assert responses["preview-1"]["ok"] is True
        assert responses["export-1"]["ok"] is True
        assert responses["preview-2"]["ok"] is True
        assert responses["export-2"]["ok"] is True
        assert responses["preview-3"]["ok"] is True
        assert responses["bye"]["ok"] is True

        default_files = {f["role"]: f["path"] for f in responses["export-1"]["result"]["files"]}
        alt_files = {f["role"]: f["path"] for f in responses["export-2"]["result"]["files"]}
        for role in ("body_stl", "assembly_step", "report_markdown"):
            default_path = Path(default_files[role])
            alt_path = Path(alt_files[role])
            assert default_path.is_file() and default_path.stat().st_size > 0
            assert alt_path.is_file() and alt_path.stat().st_size > 0
        assert (
            Path(default_files["body_stl"]).read_bytes() != Path(alt_files["body_stl"]).read_bytes()
        )

    def test_real_subprocess_preflight_overwrite_confirm_sequence(self, tmp_path):
        """Build 024 M2 §45: the real bundled-interpreter proof of the full
        M2 overwrite UX sequence — preview defaults, preflight an empty
        destination (no conflict), export into it, preflight the same
        destination again (now a conflict, since export_preflight never
        performs an export itself), export again (the "confirm overwrite"
        request) and verify it actually replaced the content, then confirm
        the sidecar is still healthy (another preview) before a clean
        shutdown. No restart, no protocol corruption, no orphan."""
        export_dir = tmp_path / "export"
        export_params = {"output_directory": str(export_dir)}
        alt_params = {
            "output_directory": str(export_dir),
            "parameters": {"schema": "zerorod-parameters/v1", "values": {"body_width": 60.0}},
        }

        lines = (
            _req("preview-1", "preview")
            + _req("preflight-empty", "export_preflight", export_params)
            + _req("export-1", "export", export_params)
            + _req("preflight-conflict", "export_preflight", export_params)
            + _req("export-2", "export", alt_params)
            + _req("preview-2", "preview")
            + _req("bye", "shutdown")
        )
        result = self._run_subprocess(lines)
        assert result.returncode == 0
        responses = {
            r["request_id"]: r
            for r in (json.loads(line) for line in result.stdout.splitlines() if line.strip())
        }
        for request_id in (
            "preview-1",
            "preflight-empty",
            "export-1",
            "preflight-conflict",
            "export-2",
            "preview-2",
            "bye",
        ):
            assert responses[request_id]["ok"] is True, responses[request_id]

        assert responses["preflight-empty"]["result"]["has_conflicts"] is False
        assert responses["preflight-empty"]["result"]["conflicts"] == []

        for entry in responses["export-1"]["result"]["files"]:
            path = Path(entry["path"])
            assert path.is_file() and path.stat().st_size > 0

        # export-1 already wrote all three files into export_dir, so
        # preflighting the *same* destination again must now report all
        # three as conflicts — proving preflight and export share the exact
        # same naming logic (zerorodcad.export.expected_output_filenames),
        # not a separately duplicated one.
        conflict_result = responses["preflight-conflict"]["result"]
        assert conflict_result["has_conflicts"] is True
        assert len(conflict_result["conflicts"]) == 3

        second_files = {
            f["role"]: Path(f["path"]) for f in responses["export-2"]["result"]["files"]
        }
        for path in second_files.values():
            assert path.is_file() and path.stat().st_size > 0
        # Same filenames (same project_name) — real overwrite-in-place, not
        # a second file set alongside the first (byte-level overwrite
        # content is already proven directly, without the batched-subprocess
        # read-only-after-the-fact limitation, by
        # test_export_overwrites_existing_output_files_in_place in
        # test_zerorod_sidecar_main.py). Here, the final on-disk report
        # reflecting the *second* export's parameters (body_width: 60, not
        # the default 38) is itself proof the overwrite actually happened
        # rather than being silently skipped.
        assert {p.name for p in second_files.values()} == {
            "cbg-open-g-body.stl",
            "cbg-open-g-assembly.step",
            "cbg-open-g-report.md",
        }
        assert "60.00 mm" in second_files["report_markdown"].read_text()

    def test_real_subprocess_paths_and_interleaving_sequence(self, tmp_path):
        """Build 024 M3 §17/§18/§19/§32: real evidence, through the actual
        VTK-free persistent interpreter, that export/preview interleaving
        never exports stale geometry, and that spaces/Unicode destination
        paths work with no shell involved (no escaping relevant — this is
        pure subprocess stdin/stdout, never a shell command)."""
        spaces_dir = tmp_path / "ZeroRod Export Test"
        unicode_dir = tmp_path / "ZeroRod – Prüfung"
        alt_params = {"schema": "zerorod-parameters/v1", "values": {"body_width": 60.0}}

        lines = (
            _req("preview-1", "preview")
            + _req("export-1", "export", {"output_directory": str(spaces_dir)})
            + _req("preview-2", "preview", alt_params)
            + _req(
                "export-2",
                "export",
                {"output_directory": str(unicode_dir), "parameters": alt_params},
            )
            + _req("preview-3", "preview")
            + _req("bye", "shutdown")
        )
        result = self._run_subprocess(lines)
        assert result.returncode == 0
        responses = {
            r["request_id"]: r
            for r in (json.loads(line) for line in result.stdout.splitlines() if line.strip())
        }
        for request_id in ("preview-1", "export-1", "preview-2", "export-2", "preview-3", "bye"):
            assert responses[request_id]["ok"] is True, responses[request_id]

        # export-1 (default params) went into the spaces path.
        default_report = None
        for entry in responses["export-1"]["result"]["files"]:
            path = Path(entry["path"])
            assert path.is_file() and path.stat().st_size > 0
            assert "ZeroRod Export Test" in str(path)
            if entry["role"] == "report_markdown":
                default_report = path.read_text()
        assert "38.00 mm" in default_report

        # export-2 (body_width=60) went into the Unicode path — proving the
        # accepted geometry at the time of THIS export call (not whatever
        # preview-1/export-1 last showed) is what actually got exported.
        alt_report = None
        for entry in responses["export-2"]["result"]["files"]:
            path = Path(entry["path"])
            assert path.is_file() and path.stat().st_size > 0
            assert "Prüfung" in str(path)
            if entry["role"] == "report_markdown":
                alt_report = path.read_text()
        assert "60.00 mm" in alt_report

    def test_real_subprocess_repeated_export_stress(self, tmp_path):
        """Build 024 M3 §31: a bounded repeated-export sequence (20 real
        exports, alternating destinations to also exercise overwrite-free
        and overwrite paths) through the same persistent process — proves
        no request corruption and a clean final shutdown. Memory growth
        during a comparable repeated-request sequence was already measured
        as part of Build 023 M4's own benchmark (≈0.18% RSS growth over 20
        requests); this test's focus is correctness/stability, not memory,
        which docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md's
        Performance/Memory section addresses separately."""
        export_count = 20
        lines = ""
        for i in range(export_count):
            destination = tmp_path / f"run-{i % 4}"  # 4 destinations, reused -> real overwrites
            lines += _req(f"export-{i}", "export", {"output_directory": str(destination)})
        lines += _req("preview-final", "preview") + _req("bye", "shutdown")

        result = self._run_subprocess(lines)
        assert result.returncode == 0
        responses = {
            r["request_id"]: r
            for r in (json.loads(line) for line in result.stdout.splitlines() if line.strip())
        }
        assert len(responses) == export_count + 2
        for i in range(export_count):
            assert responses[f"export-{i}"]["ok"] is True, responses[f"export-{i}"]
        assert responses["preview-final"]["ok"] is True
        assert responses["bye"]["ok"] is True

        for i in range(4):
            destination = tmp_path / f"run-{i}"
            files = list(destination.iterdir())
            assert len(files) == 3
            assert all(f.stat().st_size > 0 for f in files)

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
