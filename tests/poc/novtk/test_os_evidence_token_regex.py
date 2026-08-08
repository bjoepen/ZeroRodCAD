"""Tests for the TE-001 lsof/vmmap 'real vtk token' matcher (section 20, 28).

Guards against the false-positive that motivated the fix: the PoC venv is
named ``.venv-novtk-poc``, so every lsof/vmmap line for that process contains
the literal substring "vtk" (from "novtk") even when no real VTK is present.
"""

from __future__ import annotations

from tools.poc.novtk.te001_run_all import _has_real_vtk_token


def test_novtk_venv_path_is_not_a_false_positive():
    line = (
        "Python  2097 bernd  txt  REG  1,16  68736  "
        "/Users/bernd/Projekte/ZeroRodCAD-App/.venv-novtk-poc/lib/python3.13/"
        "site-packages/OCP/.dylibs/libTKXMesh.7.9.3.dylib"
    )
    assert _has_real_vtk_token(line) is False


def test_real_vtk_dylib_is_detected():
    line = (
        "Python  2097 bernd  txt  REG  1,16  68736  "
        "/some/path/site-packages/vtkmodules/libvtkCommonCore.dylib"
    )
    assert _has_real_vtk_token(line) is True


def test_uppercase_vtk_is_detected():
    assert _has_real_vtk_token("Contents/Frameworks/VTKCommonCore.framework") is True


def test_novtk_uppercase_is_not_a_false_positive():
    assert _has_real_vtk_token("cadquery_ocp_NOVTK-7.9.3.1.1.dist-info") is False
