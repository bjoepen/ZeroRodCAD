# TE-001 — Discovery

Technology Evaluation, branch `spike/te001-novtk-feasibility`. Not a production change, not
a continuation of Build 021 M2-M4 (paused after M1).

## Research question

Can ZeroRodCAD's real CAD workflows run under Python 3.13 with `cadquery-ocp-novtk` instead of
`cadquery-ocp`, with VTK never installed, imported, or natively loaded?

## Baseline

- Branch: `spike/te001-novtk-feasibility` (confirmed, not changed).
- Working tree: clean before any change.
- Python 3.13.14 available via `python3.13`.

## ZeroRodCAD CAD engine (module layout)

```
src/zerorodcad/            CAD engine (no GUI, no VTK import anywhere)
  model.py                  build_base_body / build_groove_cutter / build_channel_cutters /
                             build_body / build_rod / build_assembly  (real cadquery.Workplane/Assembly)
  parameters.py              ZeroRodParameters (pure dataclass), default_parameters()
  geometry.py                cylinder_between, fuse_all
  preview.py                 tessellate_workplane (calls Shape.tessellate()), build_preview_scene
  preview_data.py            PreviewMesh / PreviewScene — already GUI-neutral (plain tuples)
  export.py                  export_project — STL via cadquery.exporters.export, STEP via Assembly.export
  validation.py, report.py   no CAD library dependency

src/zerorodcad_desktop/    Desktop GUI (PySide6)
  preview_widget.py          from-scratch QPainter 3D widget — confirmed NOT VTK-based

src/zerorod_analysis/      Bundle/dependency analysis tooling (unrelated to CAD runtime)
  runtime/                   Build 021 M1 runtime trace foundation (reused by TE-001, see below)
```

No `vtkmodules`, `IVtk`, `IVtkOCC`, `IVtkTools`, `IVtkVTK` reference exists anywhere in
`src/zerorodcad` or `src/zerorodcad_desktop`. VTK enters ZeroRodCAD's dependency graph only
transitively, through `cadquery`'s own dependency on `cadquery-ocp` (`vtk==9.6.2` pinned) and on
`trame`/`trame-vtk`/`trame-components`/`trame-vuetify` (CadQuery's own optional Jupyter/trame
viewer, unused by ZeroRodCAD).

`docs/guides/DEPENDENCY_AUDIT.md` already states the project's position: *"VTK remains included
until a replacement runtime has passed the complete preview and export validation."* TE-001 is
that validation.

## Bundle cost of VTK (prior measurements, reused not re-derived)

- `build/reports/sprint3-phase3-vtk-analysis/vtk-total-size.txt`: 501,700 KiB (~490 MiB).
- `docs/PHASE-5-BASELINE.md`: 522.94 MiB for the VTK dylibs subset, triple-duplicated across
  `Frameworks`/`Resources`/`vtkmodules/__dot__dylibs` (part of a 1.20 GiB total redundancy per
  `docs/ECR-018-005-Bundle-Deduplication.md`).
- `libvtkCommonCore.dylib` alone: 143 MiB.

## Build 021 M1 runtime trace infrastructure (reused, not duplicated)

- `src/zerorod_analysis/runtime/{models,schema,normalize,merge,serialization}.py` — `RuntimeTrace`,
  `TraceEvidence`, `EvidenceKind` (PYTHON_MODULE, NATIVE_EXTENSION, DYLIB, FRAMEWORK, QT_PLUGIN),
  `EvidenceStatus` (OBSERVED/INFERRED/UNRESOLVED), `merge_evidence()`, `trace_json_bytes()`,
  `write_trace_atomic()`. Schema id `zerorod-analysis/runtime-trace/v1`.
- `tools/trace_runtime.py` — CLI controller built for tracing a packaged `.app` bundle:
  `parse_dyld_output()`, `parse_qt_output()`, `_read_raw()`, `collect_trace()`, `main()`.
- `packaging/macos/runtime_hook.py` — `_RuntimeRecorder`: installs `sys.addaudithook`, snapshots
  `sys.modules` at start/end, records `audit-import` and `audit-native-load` events, opt-in via
  `ZEROROD_RUNTIME_TRACE=1`.
- ADR-021-001 explicit non-goal: no second `MetaPathFinder`/parallel trace engine.
  `docs/discovery/BUILD-021-M1-RUNTIME-TRACE-DISCOVERY.md` lists retiring the old VTK-only probe
  (`tools/trace_runtime_imports.py`, now a deprecated shim) as a design goal.
- **TE-001 adapts, does not duplicate**: since TE-001 runs in a plain venv (not a `.app` bundle),
  `tools/poc/novtk/runtime_trace_adapter.py` calls `_RuntimeRecorder`/`_read_raw`/`merge_evidence`/
  `RuntimeTrace`/`write_trace_atomic` directly instead of through the bundle-oriented CLI wrapper.
  No new trace logic is written.

## Critical finding, verified against the actually-installed package (not just static reading)

`cadquery/__init__.py` (2.8.0, actually installed in this repo's `.venv`) does
`from .occ_impl.shapes import (...)` unconditionally — no try/except.
`cadquery/occ_impl/shapes.py:21` does `from vtkmodules.vtkCommonDataModel import vtkPolyData`
unconditionally. `cadquery/occ_impl/exporters/vtk.py` (reached later in the same import chain via
`cadquery/occ_impl/exporters/__init__.py:from .vtk import exportVTP`) also unconditionally imports
`vtkmodules`. This is a known, still-open upstream issue: CadQuery/cadquery#1908.

**Consequence, confirmed empirically in Phase 1 (see `Experiment.md`/`Results.md`)**: a bare
`import cadquery` fails as soon as VTK is absent — regardless of the fact that ZeroRodCAD's own
code never touches VTK. The precise failure site (via full traceback, not just static reading) is
`cadquery/occ_impl/shapes.py:21`, not `exporters/vtk.py` as the static read alone would have
suggested — `shapes.py` is imported earlier in `cadquery/__init__.py`, so it fails first.

## Package research (PyPI JSON API, verified live 2026-08-08)

| Package | Latest | Released | Python | macOS ARM64 | License | VTK dependency |
|---|---|---|---|---|---|---|
| `cadquery` | 2.8.0 | 2026-06-21 | `>=3.11` | n/a (pure Python) | Apache Public License 2.0 | via `cadquery-ocp` + required `trame`/`trame-vtk`/`trame-components`/`trame-vuetify` |
| `cadquery-ocp` | 7.9.3.1.1 | matches | cp310-cp313 wheels | yes | Apache-2.0 | `vtk==9.6.2` pinned |
| `cadquery-ocp-novtk` | 7.9.3.1.1 | 2026-05-28 | cp310-cp314 wheels | yes — `cadquery_ocp_novtk-7.9.3.1.1-cp313-cp313-macosx_11_0_arm64.whl` confirmed | Apache-2.0 | none — only `cadquery-ocp-proxy==7.9.3.1.1` |
| `cadquery-ocp-proxy` | 7.9.3.1.1 | matches | py3-none-any | yes | — | none (version-tracking proxy) |
| `vtk` | 9.6.2 | pinned by cadquery-ocp | — | — | BSD | excluded from this evaluation entirely |

Maintainers of `cadquery-ocp`/`cadquery-ocp-novtk` (`b_walter`, `jmwright`) are the same team as
upstream CadQuery — actively maintained, current release, no deprecation/abandonment signals. See
`Dependencies.md` for the full governance record.
