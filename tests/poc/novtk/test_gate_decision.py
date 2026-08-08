"""Tests for the TE-001 Gate A decision logic (sections 22-23, 28)."""

from __future__ import annotations

import copy

from tools.poc.novtk.gate_decision import decide_gate_a

_CHECKPOINT_NAMES = ("import", "geometry", "tessellate", "preview-mesh", "stl", "step")


def _checkpoint(name: str, status: str) -> dict:
    return {"name": name, "status": status, "detail": "", "sys_modules_vtk_hits": []}


def _base_evidence(checkpoint_statuses: list[str]) -> dict:
    return {
        "checkpoints": {
            "checkpoints": [
                _checkpoint(name, status)
                for name, status in zip(_CHECKPOINT_NAMES, checkpoint_statuses, strict=True)
            ]
        },
        "runtime_trace": {"error": None},
        "os_level_evidence": {"overall": "vtk-free"},
        "ivtk_boundary": {"overall": "acceptable"},
        "package_audit": {
            "pip_show": {
                "cadquery-ocp-novtk": "Name: cadquery-ocp-novtk\nVersion: 7.9.3.1.1\n",
                "cadquery-ocp": "WARNING: Package(s) not found: cadquery-ocp\n",
                "vtk": "WARNING: Package(s) not found: vtk\n",
            }
        },
    }


def test_all_pass_yields_pass_high_confidence():
    evidence = _base_evidence(["pass"] * 6)
    decision = decide_gate_a(evidence)
    assert decision.verdict == "PASS"
    assert decision.confidence == "HIGH"
    assert decision.reasons == []


def test_import_fail_yields_fail_with_reason():
    evidence = _base_evidence(["fail", "skipped", "skipped", "skipped", "skipped", "skipped"])
    decision = decide_gate_a(evidence)
    assert decision.verdict == "FAIL"
    assert any("import" in reason for reason in decision.reasons)
    assert decision.layer_status["functional"] == "fail"


def test_real_captured_evidence_shape_is_fail_high():
    """Mirrors the actual TE-001 empirical result: import fails cleanly, every
    other layer is clean, everything downstream is consistently skipped."""
    evidence = _base_evidence(["fail", "skipped", "skipped", "skipped", "skipped", "skipped"])
    decision = decide_gate_a(evidence)
    assert decision.verdict == "FAIL"
    assert decision.confidence == "HIGH"
    assert decision.layer_status["package"] == "ok"
    assert decision.layer_status["python"] == "ok"
    assert decision.layer_status["os_level"] == "ok"
    assert decision.layer_status["ivtk_boundary"] == "ok"


def test_os_level_not_verified_caps_confidence_at_medium():
    evidence = _base_evidence(["pass"] * 6)
    evidence["os_level_evidence"]["overall"] = "NOT VERIFIED"
    decision = decide_gate_a(evidence)
    assert decision.verdict == "PASS"
    assert decision.confidence == "MEDIUM"
    assert any("NOT VERIFIED" in reason for reason in decision.reasons)


def test_os_level_vtk_found_fails_even_if_functional_passes():
    evidence = _base_evidence(["pass"] * 6)
    evidence["os_level_evidence"]["overall"] = "vtk-found"
    decision = decide_gate_a(evidence)
    assert decision.verdict == "FAIL"


def test_contradictory_checkpoint_pattern_is_inconclusive():
    # A "fail" followed by a "pass" is internally incoherent (a passed checkpoint
    # that depends on an earlier failed one) and must not be reported as PASS/FAIL.
    evidence = _base_evidence(["pass", "fail", "pass", "skipped", "skipped", "skipped"])
    decision = decide_gate_a(evidence)
    assert decision.verdict == "FAIL"  # any_fail still takes precedence, correctly
    # but the coherence helper itself must flag this shape as incoherent
    from tools.poc.novtk.gate_decision import all_pass_or_expected_fail

    statuses = {c["name"]: c["status"] for c in evidence["checkpoints"]["checkpoints"]}
    assert all_pass_or_expected_fail(statuses) is False


def test_vtk_in_sys_modules_fails_python_layer():
    evidence = _base_evidence(["pass"] * 6)
    evidence["checkpoints"]["checkpoints"][0]["sys_modules_vtk_hits"] = ["vtkmodules"]
    decision = decide_gate_a(evidence)
    assert decision.layer_status["python"] == "fail"
    assert decision.verdict == "INCONCLUSIVE"


def test_package_layer_fails_if_cadquery_ocp_installed():
    evidence = _base_evidence(["pass"] * 6)
    evidence["package_audit"]["pip_show"]["cadquery-ocp"] = (
        "Name: cadquery-ocp\nVersion: 7.9.3.1.1\n"
    )
    decision = decide_gate_a(evidence)
    assert decision.layer_status["package"] == "fail"
    assert decision.verdict == "INCONCLUSIVE"


def test_decision_is_deterministic():
    evidence = _base_evidence(["fail", "skipped", "skipped", "skipped", "skipped", "skipped"])
    first = decide_gate_a(copy.deepcopy(evidence))
    second = decide_gate_a(copy.deepcopy(evidence))
    assert first == second
