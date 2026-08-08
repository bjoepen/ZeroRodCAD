"""Tests for tools/poc/novtk/runtime_trace_adapter.py's vtk_evidence() (TE-001.1).

Regression guard for a false positive found while validating the TE-001.1
patch: a module legitimately named ``cadquery.occ_impl.exporters.vtk`` (our
own patched file) must not be flagged just because "vtk" appears in its
dotted name / file path.
"""

from __future__ import annotations

from tools.poc.novtk.runtime_trace_adapter import vtk_evidence

from zerorod_analysis.runtime.models import EvidenceKind, RuntimeTrace


def _trace(**kwargs) -> RuntimeTrace:
    base = dict(
        schema="zerorod-analysis/runtime-trace/v1",
        build_id="test",
        python_version="3.13.14",
        platform="darwin",
        started_at="2026-08-08T00:00:00Z",
        ended_at="2026-08-08T00:00:01Z",
        profile="startup-test",
        exit_status="exited",
        exit_code=0,
        timed_out=False,
        incomplete=False,
    )
    base.update(kwargs)
    return RuntimeTrace(**base)


def test_cadquery_exporters_vtk_module_is_not_a_false_positive():
    from zerorod_analysis.runtime.models import TraceEvidence

    trace = _trace(
        python_modules=(
            TraceEvidence(
                identity="cadquery.occ_impl.exporters.vtk",
                kind=EvidenceKind.PYTHON_MODULE,
                bundle_relative_path="lib/python3.13/site-packages/cadquery/occ_impl/exporters/vtk.py",
            ),
        )
    )
    assert vtk_evidence(trace) == []


def test_real_vtkmodules_import_is_detected():
    from zerorod_analysis.runtime.models import TraceEvidence

    trace = _trace(
        python_modules=(
            TraceEvidence(
                identity="vtkmodules.vtkCommonDataModel", kind=EvidenceKind.PYTHON_MODULE
            ),
        )
    )
    assert vtk_evidence(trace) == ["vtkmodules.vtkCommonDataModel"]


def test_real_vtk_dylib_is_detected():
    from zerorod_analysis.runtime.models import TraceEvidence

    trace = _trace(
        loaded_libraries=(
            TraceEvidence(
                identity="lib/vtkmodules/libvtkCommonCore.dylib",
                kind=EvidenceKind.DYLIB,
            ),
        )
    )
    assert vtk_evidence(trace) == ["lib/vtkmodules/libvtkCommonCore.dylib"]


def test_novtk_venv_dylib_path_is_not_a_false_positive():
    from zerorod_analysis.runtime.models import TraceEvidence

    trace = _trace(
        loaded_libraries=(
            TraceEvidence(
                identity="lib/python3.13/site-packages/OCP/.dylibs/libTKXMesh.7.9.3.dylib",
                kind=EvidenceKind.DYLIB,
                bundle_relative_path=".venv-novtk-poc/lib/python3.13/site-packages/OCP/.dylibs/libTKXMesh.7.9.3.dylib",
            ),
        )
    )
    assert vtk_evidence(trace) == []
