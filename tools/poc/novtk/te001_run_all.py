"""TE-001 orchestrator: runs every Gate A evidence layer and writes one report.

Must be invoked with the REPO'S OWN python (not the poc venv) — it spawns the
``.venv-novtk-poc`` interpreter for every in-venv step via subprocess, exactly
like a CI/validation script would.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
POC_VENV_PYTHON = REPO_ROOT / ".venv-novtk-poc" / "bin" / "python"
REPORT_DIR = REPO_ROOT / "build" / "reports" / "te001-novtk-poc"

# Matches real "vtk"/"vtkmodules" occurrences but not the "novtk" token that is
# part of this PoC's own venv directory name (.venv-novtk-poc) and therefore
# appears in the path prefix of every single lsof/vmmap line for this process.
_REAL_VTK_TOKEN = re.compile(r"(?<!no)vtk", re.IGNORECASE)


def _has_real_vtk_token(line: str) -> bool:
    return bool(_REAL_VTK_TOKEN.search(line))


# The orchestrator itself never imports cadquery/OCP/VTK; it only reuses the
# pure-Python zerorod_analysis.runtime / tools.trace_runtime modules to build
# the report, so it can run under the plain system interpreter (matching
# pytest's own pythonpath = [".", "src"] config) without touching .venv.
for _extra in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, **kwargs)


def run_checkpoints_with_dyld() -> dict:
    from datetime import UTC, datetime

    report_path = REPORT_DIR / "checkpoints.json"
    raw_trace_path = REPORT_DIR / "raw-trace.jsonl"
    for stale in (report_path, raw_trace_path):
        stale.unlink(missing_ok=True)
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    result = _run(
        [
            str(POC_VENV_PYTHON),
            "tools/poc/novtk/run_checkpoints.py",
            "--report",
            str(report_path),
            "--raw-trace",
            str(raw_trace_path),
        ],
        env={**os.environ, "DYLD_PRINT_LIBRARIES": "1"},
    )
    checkpoints = json.loads(report_path.read_text(encoding="utf-8"))
    dyld_stderr_path = REPORT_DIR / "checkpoints-dyld-stderr.txt"
    dyld_stderr_path.write_text(result.stderr, encoding="utf-8")
    return {
        "checkpoints_report": checkpoints,
        "process_exit_code": result.returncode,
        "raw_trace_path": str(raw_trace_path),
        "dyld_stderr_path": str(dyld_stderr_path),
        "dyld_stderr_line_count": len(result.stderr.splitlines()),
        "started_at": started_at,
    }


def build_runtime_trace_report(checkpoints_result: dict) -> dict:
    """Reuses the Build 021 M1 recorder output via tools/poc/novtk/runtime_trace_adapter.py
    (models/merge/serialization straight from zerorod_analysis.runtime) instead of a second
    trace engine, per section 19.
    """
    from tools.poc.novtk import runtime_trace_adapter

    exit_code = checkpoints_result["process_exit_code"]
    trace = runtime_trace_adapter.build_trace(
        raw_path=Path(checkpoints_result["raw_trace_path"]),
        venv_root=REPO_ROOT / ".venv-novtk-poc",
        started_at=checkpoints_result["started_at"],
        exit_status="exited" if exit_code == 0 else "failed",
        exit_code=exit_code,
    )
    output_path = REPORT_DIR / "runtime-trace.json"
    runtime_trace_adapter.write_trace(trace, output_path)
    hits = runtime_trace_adapter.vtk_evidence(trace)
    return {
        "runtime_trace_path": str(output_path),
        "python_module_count": len(trace.python_modules),
        "native_extension_count": len(trace.native_extensions),
        "loaded_library_count": len(trace.loaded_libraries),
        "incomplete": trace.incomplete,
        "error": trace.error,
        "vtk_evidence_hits": hits,
        "status": "vtk-import-attempted" if hits else "vtk-free",
        "interpretation": (
            "The M1 recorder's audit-import hook fires for every import ATTEMPT, "
            "successful or not, and _read_raw() records it as PYTHON_MODULE evidence "
            "regardless of outcome. A hit here means 'vtkmodules import was attempted' "
            "(expected: that is exactly what VTKImportBlocker intercepts), NOT that VTK "
            "was actually loaded. Whether VTK was actually loaded is determined by the "
            "independent sys.modules scan in the checkpoint report (sys_modules_vtk_hits) "
            "and the OS-level lsof/vmmap evidence, both checked separately below."
        )
        if hits
        else None,
    }


def check_dyld_parser_match(dyld_stderr_path: Path) -> dict:
    """Section 20: verify the reused M1 dyld parser against this system's real output."""
    from tools.trace_runtime import parse_dyld_output

    text = dyld_stderr_path.read_text(encoding="utf-8")
    matched = parse_dyld_output(text, REPO_ROOT)
    raw_line_count = len(text.splitlines())
    return {
        "raw_dyld_lines": raw_line_count,
        "parser_matched_entries": len(matched),
        "status": "NOT VERIFIED"
        if raw_line_count > 0 and len(matched) == 0
        else ("verified" if matched or raw_line_count == 0 else "NOT VERIFIED"),
        "note": (
            "Build 021 M1 parse_dyld_output() regex expects 'loaded:' in dyld stderr; "
            "this system's DYLD_PRINT_LIBRARIES format is 'dyld[PID]: <UUID> /path' "
            "with no 'loaded:' token, so the reused parser matches 0 lines even though "
            f"{raw_line_count} real libraries were printed. lsof/vmmap are used instead "
            "as the primary OS-level evidence mechanism per section 20."
        ),
    }


def os_level_evidence() -> dict:
    """Section 20: lsof/vmmap against a live checkpoint subprocess, case-insensitive vtk scan."""
    process = subprocess.Popen(
        [str(POC_VENV_PYTHON), "tools/poc/novtk/os_evidence.py"],
        cwd=REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ready_line = ""
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if line.startswith("READY"):
            ready_line = line.strip()
            break
    if not ready_line:
        process.kill()
        process.communicate()
        return {"status": "NOT VERIFIED", "note": "os_evidence.py did not signal readiness in time"}

    pid = process.pid
    lsof = _run(["lsof", "-p", str(pid)])
    vmmap = _run(["vmmap", str(pid)])
    process.stdin.write("continue\n")
    process.stdin.flush()
    process.stdin.close()
    process.wait(timeout=10)

    lsof_vtk_hits = [line for line in lsof.stdout.splitlines() if _has_real_vtk_token(line)]
    vmmap_vtk_hits = [line for line in vmmap.stdout.splitlines() if _has_real_vtk_token(line)]
    lsof_status = "ok" if lsof.returncode == 0 else "NOT VERIFIED"
    vmmap_status = "ok" if vmmap.returncode == 0 else "NOT VERIFIED"
    return {
        "checkpoint_ready_status": ready_line,
        "pid": pid,
        "lsof_status": lsof_status,
        "lsof_vtk_hits": lsof_vtk_hits,
        "lsof_stderr": lsof.stderr.strip(),
        "vmmap_status": vmmap_status,
        "vmmap_vtk_hits": vmmap_vtk_hits,
        "vmmap_stderr": vmmap.stderr.strip(),
        "overall": "NOT VERIFIED"
        if lsof_status != "ok" or vmmap_status != "ok"
        else ("vtk-found" if lsof_vtk_hits or vmmap_vtk_hits else "vtk-free"),
    }


def ivtk_boundary() -> dict:
    report_path = REPORT_DIR / "ivtk-boundary.json"
    report_path.unlink(missing_ok=True)
    _run(
        [
            str(POC_VENV_PYTHON),
            "tools/poc/novtk/ivtk_boundary.py",
            "--report",
            str(report_path),
        ]
    )
    return json.loads(report_path.read_text(encoding="utf-8"))


def size_measurements() -> dict:
    def du(path: Path) -> str | None:
        if not path.exists():
            return None
        result = _run(["du", "-sh", str(path)])
        return result.stdout.split()[0] if result.returncode == 0 else None

    site_packages = REPO_ROOT / ".venv-novtk-poc" / "lib" / "python3.13" / "site-packages"
    return {
        "measured": {
            "venv_total": du(REPO_ROOT / ".venv-novtk-poc"),
            "OCP_package": du(site_packages / "OCP"),
            "cadquery_package": du(site_packages / "cadquery"),
            "cadquery_ocp_novtk_wheel_download_mb": 62.3,
        },
        "estimated": {},
        "prior_vtk_baseline_measured_elsewhere": {
            "source": "build/reports/sprint3-phase3-vtk-analysis/vtk-total-size.txt",
            "vtk_total_kib": 501700,
            "source_2": "docs/PHASE-5-BASELINE.md",
            "vtk_dylibs_mib": 522.94,
        },
    }


def package_audit() -> dict:
    pip = str(POC_VENV_PYTHON.parent / "pip")
    listing = _run([pip, "list"]).stdout
    check = _run([pip, "check"])
    shows = {}
    for pkg in ("cadquery", "cadquery-ocp", "cadquery-ocp-novtk", "vtk"):
        shows[pkg] = _run([pip, "show", pkg]).stdout or "NOT INSTALLED"
    return {
        "pip_list": listing,
        "pip_check_stdout": check.stdout.strip(),
        "pip_check_returncode": check.returncode,
        "pip_show": shows,
    }


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    checkpoints_result = run_checkpoints_with_dyld()
    runtime_trace = build_runtime_trace_report(checkpoints_result)
    dyld_parser_check = check_dyld_parser_match(Path(checkpoints_result["dyld_stderr_path"]))
    os_evidence = os_level_evidence()
    ivtk = ivtk_boundary()
    sizes = size_measurements()
    packages = package_audit()

    full_report = {
        "schema": "zerorodcad/te001-novtk-full-evidence/v1",
        "checkpoints": checkpoints_result["checkpoints_report"],
        "runtime_trace": runtime_trace,
        "dyld_parser_reuse_check": dyld_parser_check,
        "os_level_evidence": os_evidence,
        "ivtk_boundary": ivtk,
        "sizes": sizes,
        "package_audit": packages,
    }

    from tools.poc.novtk.gate_decision import decide_gate_a

    decision = decide_gate_a(full_report)
    full_report["gate_a"] = {
        "verdict": decision.verdict,
        "confidence": decision.confidence,
        "reasons": decision.reasons,
        "layer_status": decision.layer_status,
    }

    output_path = REPORT_DIR / "te001-full-evidence.json"
    output_path.write_text(
        json.dumps(full_report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"TE-001 full evidence report written to: {output_path}")
    print(f"Gate A: {decision.verdict} (confidence: {decision.confidence})")
    return 0 if decision.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
