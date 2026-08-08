# TE-001 — Conclusion

## Gate A: FAIL

Confidence: **HIGH**.

Reason (verbatim from `gate_decision.decide_gate_a`, reproduced deterministically by
`scripts/validate-te001-novtk.sh`): functional checkpoint(s) failed: `['import']`.

## Was the research hypothesis confirmed or refuted?

**Refuted, precisely and with a clear, distinguishing root cause** — this is a complete and
valuable TE-001 outcome, not an inconclusive or defective evaluation.

The working hypothesis (`docs/discovery/BUILD-021-M1-RUNTIME-TRACE-DISCOVERY.md` and this
evaluation's own mandate) was that ZeroRodCAD's own CAD workflows do not need VTK. **This part is
confirmed**: no file under `src/zerorodcad` or `src/zerorodcad_desktop` imports `vtk`/`vtkmodules`
anywhere, and the desktop preview widget is a from-scratch `QPainter` renderer, not a VTK widget
(`Discovery.md`). The `cadquery-ocp-novtk` package itself is a clean, actively-maintained, VTK-free
OCCT binding with full Python 3.13 / macOS ARM64 support, and its `OCP.IVtk*` bridge modules are
absent entirely from the wheel (`Results.md`, IVtk boundary — classification A on all four).

What is **not** currently possible is running ZeroRodCAD's engine through **CadQuery 2.8.0 itself**
without VTK installed: `cadquery/occ_impl/shapes.py:21` (and, redundantly,
`cadquery/occ_impl/exporters/vtk.py`) unconditionally import `vtkmodules` at module load time, with
no try/except guard. This is a known, currently-open upstream issue
(CadQuery/cadquery#1908) — not a defect in ZeroRodCAD, not a defect in `cadquery-ocp-novtk`, and
not evidence that VTK is functionally required by any ZeroRodCAD workflow. It is purely an
import-time coupling in a CadQuery module ZeroRodCAD does not use for anything
(`shapes.py`'s VTK imports back a VTK-based conversion helper; `exporters/vtk.py` backs an
unused VTP exporter — `ExportTypes.VTP`, never called by `zerorodcad.export`).

Because `import cadquery` is a precondition for every one of ZeroRodCAD's own checkpoints
(geometry, tessellation, preview-mesh, STL, STEP all go through `cadquery`/`OCP`), this single
upstream coupling is sufficient to fail Gate A outright, regardless of how clean every other layer
is. All five evidence layers (package, Python/`sys.modules`, runtime trace, OS-level, functional)
agree and corroborate this exact, single root cause with HIGH confidence — see `Results.md`.

## Recommendation

**TE-002 Tauri v2 starten: NOCH NICHT.**

Gate A did not pass, so the section-25 mandate ("nur wenn Gate A PASS") means no TE-002 Tauri v2
architecture recommendation is issued from this evaluation. The underlying premise for TE-002 (a
VTK-free `Shape.tessellate()` → mesh → Three.js pipeline) remains architecturally sound per the
CAD-engine discovery in this report, but is currently blocked upstream, not by ZeroRodCAD.

## Known, actionable path forward (outside TE-001's scope — not implemented here)

Per the strict-Gate-A-only decision made for this evaluation, no code patch was applied within
TE-001 to work around the upstream coupling. If the project wants to pursue this further, options
observed during discovery (not evaluated, not recommended — purely a pointer for a future,
separately-scoped decision) include: tracking/contributing to CadQuery/cadquery#1908 upstream, or
re-running TE-001 against a future CadQuery release once that issue is resolved. `Dependencies.md`
records the exact package versions this finding is tied to, so a re-run is reproducible once
upstream changes.

## Known limitations of this evaluation

- The reused Build 021 M1 dyld-stderr parser (`tools/trace_runtime.py:parse_dyld_output`) does not
  match this machine's `DYLD_PRINT_LIBRARIES` output format and is marked `NOT VERIFIED` for that
  specific sub-mechanism; `lsof`/`vmmap` (both explicitly mandated) were used as the primary
  OS-level evidence instead and did succeed.
- Because the `import` checkpoint fails first, the `geometry`/`tessellate`/`preview-mesh`/`stl`/
  `step` checkpoints were never actually exercised against `cadquery-ocp-novtk` in this run — they
  are marked `skipped`, not `pass`. Nothing about their outcome should be inferred one way or the
  other; only the `import` checkpoint's result is a completed observation.
- No packaged `.app`/PyInstaller build was produced in TE-001 (out of scope — a plain venv only,
  per the mandate), so a direct bundle-size before/after comparison against the ~500 MiB VTK
  baseline was not performed; only isolated-venv sizes were measured (`Results.md`).
- This evaluation is scoped to the exact versions in `Dependencies.md` (Python 3.13.14, CadQuery
  2.8.0, `cadquery-ocp-novtk` 7.9.3.1.1). A different CadQuery release could change the outcome and
  would require re-running TE-001, not assuming this conclusion still holds.
