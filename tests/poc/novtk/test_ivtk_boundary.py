"""Tests for the TE-001 IVtk boundary probe (section 18, 28)."""

from __future__ import annotations

from tools.poc.novtk.ivtk_boundary import probe


def test_nonexistent_module_classifies_as_a_importerror_no_vtk():
    result = probe("OCP.IVtkDoesNotExist")
    assert result["classification"] == "A-importerror-no-vtk"
    assert result["new_vtk_modules"] == []
    assert "Error" in result["result"]


def test_stdlib_module_import_succeeds_without_vtk():
    result = probe("json")
    assert result["classification"] == "B-import-succeeded-no-vtk"
    assert result["new_vtk_modules"] == []
