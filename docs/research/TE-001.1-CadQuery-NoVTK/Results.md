# TE-001.1 — Results

All figures below are read from `build/reports/te001-novtk-poc/te001-full-evidence.json` and
`build/reports/te0011-cadquery-novtk/checkpoints.json`, regenerated in this session against the
patched CadQuery inside `.venv-novtk-poc` (see `Patch-Analysis.md` for the exact patch).

## Patch-Gate: `import cadquery` under the active VTKImportBlocker

```
IMPORT SUCCEEDED: 2.8.0
```

No `ImportError`, no blocked-name log entry (`VTKImportBlocker.blocked_names == []` for this run).

## TE-001 checkpoints, re-run against the patched cadquery

| Checkpoint | Status | Detail |
|---|---|---|
| import | **pass** | — |
| geometry | **pass** | `objects=3 bbox=(38.00,9.00,7.65)` |
| tessellate | **pass** | `vertices=720 triangles=710` |
| preview-mesh | **pass** | `meshes=['body', 'rod'] lines=['strings']` |
| stl | **pass** | `size=116984B` |
| step | **pass** | `size=105003B` |

`sys_modules_vtk_hits` is `[]` for every single checkpoint.

A pre-existing bug in the TE-001 checkpoint script itself was found and fixed while validating
this: the geometry checkpoint read `assembly.objects.values()[0].shapes[0]`, but index 0 of a
`cq.Assembly`'s `.objects` is the *root* Assembly container itself (no shape of its own) — the
real "body"/"rod" children are at indices 1/2. This bug was never triggered during TE-001 (which
never got past the `import` checkpoint), so it does not affect TE-001's recorded FAIL result.
Fixed to use `assembly.toCompound().BoundingBox()`, which correctly combines the whole tree.
Committed as part of this evaluation (`tools/poc/novtk/run_checkpoints.py`).

A second false positive was found and fixed in `tools/poc/novtk/runtime_trace_adapter.py`'s
`vtk_evidence()`: its old path-substring heuristic flagged the (patched, VTK-free-until-called)
module `cadquery.occ_impl.exporters.vtk` purely because "vtk" appears in its own file name. Fixed
to check the dotted-module-name root for `PYTHON_MODULE`/`NATIVE_EXTENSION` evidence, and the same
`(?<!no)vtk` real-token regex already used for the OS-level lsof/vmmap scan for `DYLIB` evidence.
Covered by `tests/poc/novtk/test_runtime_trace_adapter.py`.

## Full evidence layers (all five, section 21)

- **Package**: `cadquery-ocp-novtk` 7.9.3.1.1 installed; `cadquery-ocp` and `vtk` both absent
  (`pip show` → `WARNING: Package(s) not found` for both). `pip check` shows the same
  pre-existing metadata-naming mismatch as TE-001 (cadquery formally wants `cadquery-ocp`
  + `trame*`) — unrelated to this patch, already documented as non-disqualifying in TE-001.
- **Python / `sys.modules`**: `[]` VTK hits after every checkpoint, including the four checkpoints
  that TE-001 never reached.
- **Runtime trace** (Build 021 M1, reused verbatim): `python_module_count: 1055`,
  `native_extension_count: 39`, `loaded_library_count: 1`, `incomplete: False`, `error: None`,
  `vtk_evidence_hits: []` (after the `vtk_evidence()` fix above — before the fix it incorrectly
  reported `['cadquery.occ_impl.exporters.vtk']`, a false positive, not a real load).
- **OS-level** (`lsof -p PID` / `vmmap PID`, real-token regex): `lsof_vtk_hits: []`,
  `vmmap_vtk_hits: []`, both tools `ok`. `overall: vtk-free`.
- **Functional**: all six checkpoints `pass` (table above).

## IVtk boundary (unaffected by this patch, re-confirmed)

Still classification A (ImportError, no VTK load) for all four `OCP.IVtk*` submodules — this
patch does not and cannot change this, since those submodules are simply absent from the
`cadquery-ocp-novtk` build (a property of the OCP wheel, not of CadQuery's Python code). `overall:
acceptable`.

## VTK-specific functions still fail cleanly (Patch-Gate requirement)

Verified directly (not simulated), without VTK installed:

| Call | Result |
|---|---|
| `Shape.toVtkPolyData()` | `ImportError: VTK is required for Shape.toVtkPolyData(). Install the 'vtk' package (e.g. use the 'cadquery-ocp' distribution instead of 'cadquery-ocp-novtk') to use this feature.` |
| `exporters.export(shape, path, exportType="VTP")` | `ImportError: VTK is required for this CadQuery VTK/VTP feature. ...` |
| `cadquery.occ_impl.assembly.toVTK(assembly)` | `ImportError: VTK is required for toVTK()/the interactive VTK preview. ...` |
| `assembly.export(path, exportType="VTKJS")` | `ImportError: VTK is required for VTKJS export. ...` |

All four: clean `ImportError`, informative message, `sys.modules` still `[]` for `vtk`/`vtkmodules`
afterward — no silent malfunction, no VTK partially loaded then abandoned.

## Backward compatibility — verified empirically, not just asserted

`.venv-novtk-poc` was **temporarily** switched from `cadquery-ocp-novtk` to real `cadquery-ocp`
7.9.3.1.1 (which pulls in `vtk==9.6.2`) to test the patched code with VTK actually present, then
switched back to `cadquery-ocp-novtk` afterward (state restored, reproducible, confirmed by
re-running the full evidence collection: Gate A still PASS/HIGH after restoration).

With real `cadquery-ocp` + `vtk` installed, on the same patched code:

| Call | Result |
|---|---|
| `Shape.toVtkPolyData()` | `PolyData`, 1869 points — works |
| `exporters.export(..., exportType="VTP")` | file written, 6618 bytes — works |
| `cadquery.occ_impl.assembly.toVTK(assembly)` | `vtkOpenGLRenderer` — works |
| `assembly.export(..., exportType="VTKJS")` | file written — works |
| STL/STEP export (`export_project`) | 116984B / 105003B — **identical sizes** to the no-VTK run |

One important discovery from this check: simply `pip install vtk` on top of
`cadquery-ocp-novtk` does **not** restore VTK functionality — `OCP.IVtkOCC`/`OCP.IVtkVTK` (used by
`toVtkPolyData()`) are compiled-in bridge classes that are entirely absent from the
`cadquery-ocp-novtk` wheel itself, independent of whether the pure-Python `vtk` package is present.
Full VTK functionality requires the `cadquery-ocp` distribution (which ships those bridge classes),
not `cadquery-ocp-novtk` + `vtk`. This is a novtk-package property, not something this patch
changes or could change.

## Test suite

`pytest tests/poc/novtk/ -v`: 39 passed, 1 skipped (the TE-001 regression-guard test correctly
self-detected the changed situation: *"cadquery no longer eagerly imports vtkmodules at import
time; re-run the full TE-001 evidence gathering, this changes the Gate A outcome"* — exactly the
situation TE-001.1 produced). Full repo suite: 193 passed, 1 skipped, no regressions.
