"""TE-001 Gate A decision logic (sections 22-23).

Pure function over the assembled evidence dict produced by
``tools/poc/novtk/te001_run_all.py`` — kept separate and side-effect free so it
can be unit tested deterministically without spawning subprocesses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateADecision:
    verdict: str  # "PASS" | "FAIL" | "INCONCLUSIVE"
    confidence: str  # "HIGH" | "MEDIUM" | "LOW"
    reasons: list[str] = field(default_factory=list)
    layer_status: dict[str, str] = field(default_factory=dict)


def _package_layer_ok(package_audit: dict) -> bool:
    shows = package_audit.get("pip_show", {})
    novtk_installed = "Name: cadquery-ocp-novtk" in shows.get("cadquery-ocp-novtk", "")
    ocp_absent = shows.get("cadquery-ocp", "NOT INSTALLED").strip() in (
        "",
        "NOT INSTALLED",
    ) or "WARNING: Package(s) not found" in shows.get("cadquery-ocp", "")
    vtk_absent = shows.get("vtk", "NOT INSTALLED").strip() in (
        "",
        "NOT INSTALLED",
    ) or "WARNING: Package(s) not found" in shows.get("vtk", "")
    return novtk_installed and ocp_absent and vtk_absent


def _python_layer_ok(checkpoints: list[dict]) -> bool:
    return all(len(c.get("sys_modules_vtk_hits", [])) == 0 for c in checkpoints)


def decide_gate_a(evidence: dict) -> GateADecision:
    checkpoints = evidence["checkpoints"]["checkpoints"]
    statuses = {c["name"]: c["status"] for c in checkpoints}
    any_fail = any(status == "fail" for status in statuses.values())
    all_pass = all(status == "pass" for status in statuses.values())
    failed_names = [name for name, status in statuses.items() if status == "fail"]

    package_ok = _package_layer_ok(evidence["package_audit"])
    python_ok = _python_layer_ok(checkpoints)
    ivtk_ok = evidence["ivtk_boundary"]["overall"] == "acceptable"
    os_evidence = evidence["os_level_evidence"]
    os_overall = os_evidence.get("overall")
    os_ok = os_overall == "vtk-free"
    os_not_verified = os_overall == "NOT VERIFIED"
    os_vtk_found = os_overall == "vtk-found"

    runtime_trace = evidence["runtime_trace"]
    # A runtime-trace "vtk-import-attempted" hit is expected and NOT disqualifying by
    # itself: the M1 recorder's audit hook records every import attempt, blocked or
    # not (see runtime_trace_adapter interpretation note). Only sys.modules (python_ok)
    # and OS-level (os_ok) evidence prove whether VTK actually loaded.
    runtime_trace_ok = not runtime_trace.get("error")

    reasons: list[str] = []
    layer_status = {
        "package": "ok" if package_ok else "fail",
        "python": "ok" if python_ok else "fail",
        "runtime_trace": "ok" if runtime_trace_ok else "fail",
        "os_level": "ok" if os_ok else ("not_verified" if os_not_verified else "fail"),
        "ivtk_boundary": "ok" if ivtk_ok else "fail",
        "functional": "pass" if all_pass else ("fail" if any_fail else "incomplete"),
    }

    if any_fail:
        verdict = "FAIL"
        reasons.append(f"functional checkpoint(s) failed: {failed_names}")
    elif not all_pass:
        verdict = "INCONCLUSIVE"
        reasons.append("not all checkpoints reached a pass/fail outcome")
    elif not (package_ok and python_ok and ivtk_ok and runtime_trace_ok):
        verdict = "INCONCLUSIVE"
        reasons.append("a required evidence layer did not confirm a clean state")
    elif os_vtk_found:
        verdict = "FAIL"
        reasons.append("OS-level evidence (lsof/vmmap) found a real VTK library")
    else:
        verdict = "PASS"

    if not package_ok:
        reasons.append("package layer: cadquery-ocp-novtk/cadquery-ocp/vtk state not as required")
    if not python_ok:
        reasons.append("python layer: sys.modules contains vtk/vtkmodules")
    if not ivtk_ok:
        reasons.append("IVtk boundary: real VTK load observed")
    if os_not_verified:
        reasons.append("OS-level evidence NOT VERIFIED (lsof/vmmap unavailable or failed)")

    mandatory_layers_ok = (
        package_ok and python_ok and runtime_trace_ok and all_pass_or_expected_fail(statuses)
    )
    if mandatory_layers_ok and os_ok and ivtk_ok:
        confidence = "HIGH"
    elif mandatory_layers_ok and os_not_verified:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return GateADecision(
        verdict=verdict,
        confidence=confidence,
        reasons=reasons,
        layer_status=layer_status,
    )


def all_pass_or_expected_fail(statuses: dict[str, str]) -> bool:
    """True if checkpoints resolved cleanly: either everything passed, or a
    single checkpoint failed and every checkpoint after it was (consistently)
    skipped as a consequence — i.e. the evidence is internally coherent, not
    contradictory (section 23's INCONCLUSIVE trigger is reserved for the latter).
    """
    values = list(statuses.values())
    if all(status == "pass" for status in values):
        return True
    if "fail" not in values:
        return False
    first_fail = values.index("fail")
    before = values[:first_fail]
    after = values[first_fail + 1 :]
    return all(status == "pass" for status in before) and all(
        status == "skipped" for status in after
    )
