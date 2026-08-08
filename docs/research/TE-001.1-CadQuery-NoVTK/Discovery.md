# TE-001.1 — Discovery

Technology Evaluation, branch `spike/te0011-cadquery-novtk-decoupling` (created from the
`spike/te001-novtk-feasibility` commit). Not a production change, not a permanent CadQuery fork.

## Goal

Determine and prove the smallest possible change to CadQuery 2.8.0 that allows `import cadquery`
to succeed without `vtk`/`vtkmodules` installed, while every non-VTK function keeps working
unchanged — building directly on TE-001's finding that `import cadquery` fails under
`cadquery-ocp-novtk` because CadQuery's own package unconditionally imports `vtkmodules`.

## Scope note: four named files were necessary but not sufficient

The mandate named four files to investigate:
`cadquery/__init__.py`, `cadquery/occ_impl/shapes.py`, `cadquery/occ_impl/exporters/vtk.py`,
`cadquery/occ_impl/exporters/__init__.py`. Investigating those four honestly required following
the *entire* `import cadquery` chain, which surfaced **two more files with the identical
unconditional-import problem** that are not optional: `cadquery/occ_impl/assembly.py` and
`cadquery/occ_impl/exporters/assembly.py`. Both are reached via `cadquery/__init__.py:40`
(`from .assembly import Assembly, Color, Constraint, Material`, i.e. `cadquery/assembly.py`,
which itself imports both of these `occ_impl` modules). Patching only the four originally-named
files would still leave `import cadquery` failing. This is documented here transparently rather
than silently narrowing scope to match the original four-file list.

`cadquery/vis.py` and `cadquery/fig.py` also import `vtkmodules` unconditionally (interactive
viewer/figure modules) but are **not** imported by `cadquery/__init__.py` at all — out of scope,
not on the `import cadquery` failure path, not touched.

## Exhaustive VTK import inventory (every module-level, unconditional `vtk`/`vtkmodules`/`OCP.IVtk*`
import found in the installed CadQuery 2.8.0 package, verified by direct search of the actually
installed files in `.venv-novtk-poc`)

| File | Line(s) | Names imported | Consuming function/class | Runtime purpose |
|---|---|---|---|---|
| `occ_impl/shapes.py` | 21-22 | `vtkPolyData` (type-annotation only), `vtkTriangleFilter`, `vtkPolyDataNormals` | `Shape.toVtkPolyData()` (line 1675) | Converts an OCCT shape to a `vtkPolyData` mesh — the shared VTK-mesh conversion helper used by every other VTK-based export/preview path below. |
| `occ_impl/shapes.py` | 297-298 | `IVtkOCC_Shape`, `IVtkOCC_ShapeMesher` (from `OCP.IVtkOCC`), `IVtkVTK_ShapeData` (from `OCP.IVtkVTK`) | `Shape.toVtkPolyData()` (line 1675) | OCP's own VTK-bridge classes used inside the same method — **absent entirely** from the `cadquery-ocp-novtk` build (confirmed in TE-001's IVtk boundary test: classification A, `ModuleNotFoundError` for all four `OCP.IVtk*` submodules). |
| `occ_impl/exporters/vtk.py` | 1-11 | `vtkXMLPolyDataWriter`, `vtkAppendPolyData` (imported but never used anywhere in the file — pre-existing dead import, not introduced by this patch), `vtkPolyData`, `vtkExtractCellsByType`, `VTK_TRIANGLE`, `VTK_LINE`, `VTK_VERTEX`, `VTK_POLY_LINE` | `extractEdgesFaces()`, `exportVTP()`, `toString()` | The VTP-export module. Every function in this file is VTK-only; ZeroRodCAD never calls `ExportTypes.VTP`. |
| `occ_impl/exporters/__init__.py` | 19 | `exportVTP` (from `.vtk`) | `export()`'s `ExportTypes.VTP` branch (line 136) | Only *re-exports* the name; does not itself import `vtkmodules` — its module-level failure was a downstream consequence of `exporters/vtk.py`'s own unconditional imports, not its own. No direct fix needed here (confirmed empirically after patching `vtk.py`). |
| `occ_impl/assembly.py` | 44-49 | `vtkActor`, `vtkPolyDataMapper as vtkMapper`, `vtkRenderer`, `vtkProp3D` | `toVTKAssy()` (line 618), `toVTK()` (line 668) | Builds VTK actor/renderer objects for CadQuery's own interactive VTK viewer. Not used by `Assembly.export()` for STEP (verified by reading `cadquery/assembly.py:606-623`: STEP dispatches to `exportAssembly()`, an unrelated OCP/XCAF function). |
| `occ_impl/exporters/assembly.py` | 9-10 | `vtkJSONSceneExporter`, `vtkVRMLExporter` (from `vtkmodules.vtkIOExport`), `vtkRenderWindow` (from `vtkmodules.vtkRenderingCore`) | `_vtkRenderWindow()` (line 391), `exportVTKJS()` (line 408), `exportVRML()` (line 424, assembly-level VRML, distinct from the single-shape VRML path) | Assembly-level VTKJS/VRML export helpers, reached only for `exportType in {"VTKJS", "VRML"}` — ZeroRodCAD only ever calls `exportType="STEP"`. |

**Every single one of these seven import statements backs a function ZeroRodCAD's own code never
calls** (confirmed against `Discovery.md` in TE-001: `zerorodcad.export.export_project()` only
calls `cadquery.exporters.export(..., exportType` inferred as `"STL"`) and
`assembly.export(...)` inferred as `"STEP"`).

Type-annotation-only uses (`-> vtkPolyData`, `-> List[vtkProp3D]`, `-> vtkRenderer`,
`-> vtkRenderWindow`) require no runtime import at all once `from __future__ import annotations`
(PEP 563) is active in the file — `shapes.py` already had it; `exporters/vtk.py`,
`occ_impl/assembly.py`, and `occ_impl/exporters/assembly.py` did not and needed it added (one line
each) so the now-unimported names in bare (unquoted) return-type annotations don't raise
`NameError` at function-definition time.
