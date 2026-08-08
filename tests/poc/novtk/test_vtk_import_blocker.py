"""Tests for the TE-001 VTKImportBlocker (section 11 + section 28)."""

from __future__ import annotations

import sys

import pytest
from tools.poc.novtk.vtk_import_blocker import VTKImportBlocker, install, uninstall


def test_blocks_bare_vtk():
    blocker = VTKImportBlocker()
    with pytest.raises(ImportError, match="VTK import blocked during TE-001: vtk"):
        blocker.find_spec("vtk")
    assert blocker.blocked_names == ["vtk"]


def test_blocks_bare_vtkmodules():
    blocker = VTKImportBlocker()
    with pytest.raises(ImportError, match="VTK import blocked during TE-001: vtkmodules"):
        blocker.find_spec("vtkmodules")
    assert blocker.blocked_names == ["vtkmodules"]


def test_blocks_vtkmodules_submodule():
    blocker = VTKImportBlocker()
    with pytest.raises(ImportError, match="vtkmodules.vtkCommonDataModel"):
        blocker.find_spec("vtkmodules.vtkCommonDataModel")
    assert blocker.blocked_names == ["vtkmodules.vtkCommonDataModel"]


def test_blocks_case_insensitively():
    blocker = VTKImportBlocker()
    with pytest.raises(ImportError):
        blocker.find_spec("VTK")
    with pytest.raises(ImportError):
        blocker.find_spec("VtkModules.Foo")


@pytest.mark.parametrize("name", ["os", "json", "cadquery", "OCP", "vtkish", "notvtk", "pyvtk"])
def test_does_not_block_unrelated_names(name):
    blocker = VTKImportBlocker()
    assert blocker.find_spec(name) is None
    assert blocker.blocked_names == []


def test_install_inserts_at_front_of_meta_path():
    before = list(sys.meta_path)
    blocker = install()
    try:
        assert sys.meta_path[0] is blocker
    finally:
        uninstall(blocker)
    assert sys.meta_path == before


def test_uninstall_removes_blocker_cleanly():
    blocker = install()
    assert blocker in sys.meta_path
    uninstall(blocker)
    assert blocker not in sys.meta_path


def test_uninstall_is_idempotent():
    blocker = install()
    uninstall(blocker)
    uninstall(blocker)  # must not raise
    assert blocker not in sys.meta_path


def test_blocked_names_accumulate_across_multiple_attempts():
    blocker = VTKImportBlocker()
    for name in ("vtkmodules.vtkCommonDataModel", "vtkmodules"):
        with pytest.raises(ImportError):
            blocker.find_spec(name)
    assert blocker.blocked_names == ["vtkmodules.vtkCommonDataModel", "vtkmodules"]
