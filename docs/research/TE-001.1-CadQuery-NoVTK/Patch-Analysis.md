# TE-001.1 — Patch Analysis

The actual patch (applied only to the isolated `.venv-novtk-poc`'s installed `cadquery` copy, not
a fork, not committed as a productive dependency change) is preserved as unified diffs in
`patches/` next to this file, generated against the unmodified CadQuery 2.8.0 files as installed
from PyPI, for full reproducibility:

- `patches/01-occ_impl-shapes.py.diff`
- `patches/02-occ_impl-exporters-vtk.py.diff`
- `patches/03-occ_impl-assembly.py.diff`
- `patches/04-occ_impl-exporters-assembly.py.diff`

## Decoupling options considered (section "Phase 1")

**A. Lazy import directly in the VTK-dependent function.**
Move the `from vtkmodules... import ...` statement from module scope into the function body that
actually uses it. Simplest possible change; the function's first line(s) become an import instead
of a name already being in scope. No behavior change when VTK *is* installed (same objects,
imported a few nanoseconds later, once, on first call — Python caches the import).

**B. Optional import with `try/except ImportError` and a clear runtime error.**
Same as A, but wraps the import so that a *missing* VTK produces one specific, actionable
`ImportError` at the point of use, instead of a raw `ModuleNotFoundError: No module named
'vtkmodules'` bubbling up from deep inside the function body (e.g. from the 3rd line of a 40-line
method). Directly satisfies the mandate's "VTP export requested → klare informative Exception,
keine stille Fehlfunktion".

**C. `TYPE_CHECKING`-only import.**
Applicable only where a VTK name is used *purely* as a type annotation and never as a runtime
value. Found exactly one such case: `vtkPolyData` in `shapes.py`'s
`def toVtkPolyData(...) -> vtkPolyData:` return annotation — never instantiated or referenced
inside the method body. Because `shapes.py` already has `from __future__ import annotations`
(PEP 563), the annotation is stored as an unevaluated string; the import can simply be dropped
entirely rather than moved to `TYPE_CHECKING` — an even smaller change than option C as usually
practiced. Where a file *lacked* `from __future__ import annotations` (three of the four other
files) and had a bare (unquoted) VTK-typed return annotation, the smallest fix was to add that
one future-import line, which has the same effect as `TYPE_CHECKING` guarding for every annotation
in the file at once, without touching each signature individually.

**D. Conditional import in `exporters/vtk.py`, deferred to actual VTP-export time.**
This is option A/B applied specifically to the VTP exporter module. Confirmed as the correct
approach for that file — and, once applied, `exporters/__init__.py`'s existing
`from .vtk import exportVTP` (unconditional module import of the whole submodule) automatically
stops requiring VTK too, since the submodule itself no longer does anything VTK-related at import
time. **No change to `exporters/__init__.py` was needed at all** — an import-time coupling doesn't
need fixing at every level of the chain, only at its root.

## Decision: A + B combined, per function, applied at all five real chokepoints

Every chokepoint in `Discovery.md`'s table got the same minimal, repeated pattern:

```python
def some_vtk_only_function(...):
    try:
        from vtkmodules.some_module import SomeClass
    except ImportError as exc:
        raise ImportError(
            "VTK is required for <this feature>. Install the 'vtk' package (e.g. use "
            "the 'cadquery-ocp' distribution instead of 'cadquery-ocp-novtk') to use "
            "this feature."
        ) from exc
    ...
```

No shared helper/abstraction was introduced across files or functions (would be the "breite
Refaktorierung" the mandate explicitly rules out) — each function keeps its own small,
independently-readable try/except, matching option B literally. Within a single file
(`exporters/vtk.py`) a tiny private `_VTK_IMPORT_ERROR_MESSAGE` string constant is shared across
its three functions purely to avoid repeating one sentence three times in one file — not a
cross-file abstraction.

## Patch size

| File | Diff (`diff -u`, real/unrefactored count) | True semantic change |
|---|---|---|
| `occ_impl/shapes.py` | +10 / -6 | 2 import lines removed at top (vtkPolyData annotation-only, dropped entirely), 2 import lines removed lower (IVtkOCC/IVtkVTK), one 8-line try/except added inside `toVtkPolyData()`. |
| `occ_impl/exporters/vtk.py` | +67 / -73 (**diff-tool artifact**, see below) | 11 import lines removed at top; `from __future__ import annotations` + one shared error-message constant (6 lines) added; three ~4-line try/except blocks added, one per function. True net change is roughly +20/-11 lines of substance — the larger raw diff count is an artifact of `diff` losing context alignment after a blank line was removed following each function signature (every subsequent line shifts by one, so the tool reports near-total-file replacement even though most lines are byte-identical). |
| `occ_impl/assembly.py` | +18 / -7 | 6-line top-level VTK import removed; `from __future__ import annotations` added (2 lines incl. blank); two ~7-line try/except blocks added, one each in `toVTKAssy()`/`toVTK()`. |
| `occ_impl/exporters/assembly.py` | +26 / -3 | 2-line top-level VTK import removed; `from __future__ import annotations` added; three try/except blocks added (`_vtkRenderWindow()`, `exportVTKJS()`, `exportVRML()`). |
| `occ_impl/exporters/__init__.py` | +0 / -0 | No change — becomes VTK-free automatically once `exporters/vtk.py` is fixed. |
| `cadquery/__init__.py` | +0 / -0 | No change — becomes VTK-free automatically once its four transitively-imported submodules are fixed. |

**Total: 4 files touched, 0 files added, 0 files deleted, 0 new dependencies.** Every VTK-specific
function, class, and public name that existed before the patch still exists, with an unchanged
signature and unchanged behavior when VTK *is* installed.

## API impact

None observable from outside the four patched modules. No public function signature changed
(parameter lists, return types, and default values are all unchanged). No public name was removed,
renamed, or added. `ExportTypes.VTP` and `"VTKJS"`/`"VRML"` assembly export still exist and still
work exactly as before *when VTK is installed* — verified in `Results.md`.

## Backward compatibility

Full. With VTK installed, every patched function imports the exact same names it always did, just
a few lines later (on first call instead of at module-import time) — Python caches the import, so
repeated calls have no added cost after the first. No behavior, output, or exception type changes
for the VTK-installed case (verified: `Results.md` "with VTK installed" checks, not simulated —
actually re-run against the productive `.venv` which does have `vtk` installed).

## Behavior with VTK installed vs. without

- **With VTK installed** (e.g. the productive `.venv`, or `cadquery-ocp` instead of
  `cadquery-ocp-novtk`): `import cadquery` succeeds exactly as before (a few internal imports move
  from module-load time to first-call time, invisibly). All VTK-based functions
  (`toVtkPolyData()`, `exportVTP()`, `toVTK()`/`toVTKAssy()`, `exportVTKJS()`, assembly `exportVRML()`)
  work identically to the unpatched version.
- **Without VTK installed** (this evaluation's `.venv-novtk-poc`): `import cadquery` succeeds. All
  non-VTK functions (geometry, tessellation, STL export, STEP export, and everything else in the
  package that never touches VTK) work identically. Calling any VTK-only function raises a single,
  specific `ImportError` with an actionable message — never a silent no-op, never a confusing raw
  `ModuleNotFoundError` from deep inside VTK-specific internals, never a crash somewhere unrelated.

## Tests that would be worth adding upstream

1. `import cadquery` succeeds with `vtk`/`vtkmodules` unimportable (the exact TE-001 checkpoint).
2. Every VTK-only public entry point (`Shape.toVtkPolyData`, `exporters.export(..., "VTP")`,
   `cadquery.occ_impl.assembly.toVTK`/`toVTKAssy`, `Assembly.export(..., "VTKJS")`,
   `Assembly.export(..., "VRML")`) raises `ImportError` (not some other exception type, not a
   silent failure) with VTK absent.
3. The existing VTK-based test suite (STL/STEP/geometry tests already pass without VTK; any
   existing `toVtkPolyData`/VTP/VTKJS tests should be parametrized or skipped when VTK is absent
   rather than assumed always-present).
4. A `pytest.importorskip("vtk")`-gated CI job variant that installs `cadquery-ocp-novtk` instead
   of `cadquery-ocp` and runs the full non-VTK test suite, to prevent future regressions of this
   exact decoupling.

## Relation to CadQuery/cadquery#1908

Issue #1908 ("pip install is missing vtkmodules for CadQuery 2.6.0") reports the *symptom* from the
opposite direction: users who *want* VTK get a `ModuleNotFoundError` because `setup.py`'s
declared dependencies didn't include the VTK packages CadQuery's code actually imports. This patch
addresses the *root cause* common to both framings — CadQuery's core package unconditionally
imports VTK for features most users (interactive-viewer-less, non-Jupyter, no VTP/VTKJS export)
never touch. Making these imports lazy would make #1908 structurally impossible to recur (nothing
to forget declaring, since nothing is required at package-import time) while also enabling the
VTK-optional use case this evaluation is chasing. This patch does not claim to *resolve* #1908 as
filed (it doesn't address the `trame`/`trame-vtk` install-order problem discussed in the linked
`ocp-build-system` issue) — it addresses the same underlying architectural issue from a different
angle.

## No claim of upstream acceptance

This is a working, tested, isolated patch against one specific CadQuery release (2.8.0), applied
to a `pip`-installed site-packages copy for evaluation purposes only — not a submitted PR, not a
guarantee CadQuery's maintainers would accept this exact shape of change (they may prefer a single
shared `_require_vtk()` helper, a `vtk` extras_require gate, or a different error message
convention). It demonstrates the change is *small, mechanical, and self-consistent enough to be a
plausible upstream PR*, nothing more.
