# TE-001.2 — Packaging

## No-VTK environment

`.venv-novtk-bundle` (new, isolated, `python3.13 -m venv .venv-novtk-bundle`, no
`--system-site-packages`). Productive `.venv` and TE-001/TE-001.1's `.venv-novtk-poc` were not
touched.

Install sequence (identical strategy to TE-001/TE-001.1, extended with packaging deps):

```
pip install "cadquery-ocp-novtk==7.9.3.1.1"
pip install "cadquery==2.8.0" --no-deps
pip install "ezdxf>=1.3.0" "multimethod<2.0,>=1.11" "nlopt<3.0,>=2.9.0" "runtype" "casadi" \
            "pyparsing>=3.0.0" "scipy" "numba"
pip install "PySide6>=6.7,<7" "PyInstaller>=6.16,<7"     # matches packaging/macos/requirements-build.txt pins
pip install -e . --no-deps                                # zerorodcad-desktop itself, editable
```

Package versions installed: `cadquery` 2.8.0, `cadquery-ocp-novtk` 7.9.3.1.1, `PySide6` 6.11.1
(+`PySide6_Essentials`/`PySide6_Addons`/`shiboken6`), `PyInstaller` 6.21.0
(+`pyinstaller-hooks-contrib` 2026.6). `cadquery-ocp` and `vtk`: not installed
(`pip show` → `WARNING: Package(s) not found` for both).

## TE-001.1 patch application

Per the mandate: reuse the exact already-validated patch, do not design a new one. The four
patched files (`cadquery/occ_impl/shapes.py`, `cadquery/occ_impl/exporters/vtk.py`,
`cadquery/occ_impl/assembly.py`, `cadquery/occ_impl/exporters/assembly.py`) were copied verbatim
from `.venv-novtk-poc`'s already-patched CadQuery 2.8.0 install into `.venv-novtk-bundle`, after
confirming both venvs installed the byte-identical unpatched wheel (`exporters/__init__.py`,
untouched by the patch, has identical MD5 in both venvs — proof the underlying wheel is the same,
so copying the patched files is equivalent to reapplying the same patch). No adaptation was
needed — **the patch did not need to change for packaging**, so no STOP/documentation-of-why was
triggered by section 3 of the mandate.

Verified active before building: `import cadquery` succeeds under the active `VTKImportBlocker`
(`IMPORT SUCCEEDED: 2.8.0`).

## Pre-build package audit (section 9)

```
pip list        → cadquery-ocp-novtk 7.9.3.1.1 present; no cadquery-ocp; no vtk
pip check       → cadquery 2.8.0 requires cadquery-ocp, trame, trame-components, trame-vtk,
                   trame-vuetify — all "not installed" (same pre-existing metadata-naming
                   mismatch already documented in TE-001/TE-001.1, not a new issue, not faked)
pip show cadquery              → 2.8.0
pip show cadquery-ocp          → WARNING: Package(s) not found
pip show cadquery-ocp-novtk    → 7.9.3.1.1
pip show vtk                   → WARNING: Package(s) not found
pip show PySide6               → 6.11.1
pip show pyinstaller           → 6.21.0
```
Matches the expected state exactly: `cadquery-ocp-novtk` yes, `cadquery-ocp` no, `vtk` no.

## Pre-build functional sanity check (section 10)

Reused `tools/poc/novtk/run_checkpoints.py` (TE-001's checkpoint runner) unmodified, against
`.venv-novtk-bundle`, before touching PyInstaller — to rule out a later build failure being
mistaken for a broken Python environment:

| Checkpoint | Result |
|---|---|
| import | pass |
| geometry | pass — `objects=3 bbox=(38.00,9.00,7.65)` |
| tessellate | pass — `vertices=720 triangles=710` |
| preview-mesh | pass — `meshes=['body','rod'] lines=['strings']` |
| stl | pass — `size=116984B` |
| step | pass — `size=105003B` |

Identical figures to TE-001.1's own results — confirms `.venv-novtk-bundle` reproduces the same
validated no-VTK behavior before packaging begins.

## Packaging configuration changes (minimal, documented, both env-gated and reversible)

Two files touched, both changes **opt-in via environment variable**, default (productive VTK)
behavior fully unchanged:

**`scripts/runtime_import_probe.py`**: added `ZERORODCAD_SKIP_VTK_PROBE` env-var gate. Unset (the
existing default): behaves exactly as before, still checks `vtkmodules.vtkCommonCore`/
`vtkmodules.vtkCommonDataModel`. Set: skips those two entries only, everything else (PySide6,
cadquery, OCP, zerorodcad.*) still checked. Needed because `scripts/build_macos_app.sh` runs this
probe as a pre-flight gate and would otherwise abort (exit 1) before ever invoking PyInstaller,
since `vtkmodules` is intentionally absent from `.venv-novtk-bundle`.

**`packaging/macos/ZeroRodCAD.spec`**: added `_novtk_bundle = bool(os.environ.get
("ZERORODCAD_NOVTK_BUNDLE"))`. Unset: hiddenimports/excludes identical to before (still
hidden-imports `vtkmodules.vtkCommonCore`/`vtkmodules.vtkCommonDataModel`). Set: those two
hiddenimports are omitted, and `vtk`/`vtkmodules` are added to `excludes` (defense-in-depth only —
they aren't installed in this venv at all, so this is inert, but makes the no-VTK intent explicit
and guards against any PyInstaller hook pulling them in unexpectedly). `ZeroRodCAD-Debug.spec`
inherits this automatically (it string-substitutes the release spec's source, not an independent
copy).

No other packaging file was changed. `datas`/`binaries`/`hookspath`/`runtime_hooks`/icon/bundle
identifier/Info.plist: all unchanged.

## Build result

```
ZERORODCAD_NOVTK_BUNDLE=1 .venv-novtk-bundle/bin/pyinstaller --noconfirm --clean \
  --log-level INFO packaging/macos/ZeroRodCAD.spec
```

Build completed successfully: `Build complete! The results are available in:
/Users/bernd/Projekte/ZeroRodCAD-App/dist`. Bundle: `dist/ZeroRodCAD Desktop.app`, 381M (`du -sh`),
449 files (`find -type f | wc -l`).

**No VTK files after the build, without any manual deletion step** — the build produces this state
directly (verified in `Bundle-Analysis.md`).

### Build log analysis (section 12)

- `grep -i vtk` on the full build log: 39 hits, **all** are the venv path
  `.venv-novtk-bundle` (the substring "vtk" inside "novtk"), confirmed by re-grepping with that
  false-positive excluded → 0 real hits.
- No `Processing standard module hook 'hook-vtk...'` line appears anywhere — PyInstaller's own VTK
  hook (`pyinstaller-hooks-contrib`'s `add_vtkmodules_dependencies()`, the mechanism TE-001's
  discovery traced as a prior source of auto-injected VTK hidden-imports) never activates, because
  it can only fire when `vtkmodules` is actually importable/present in the environment — which it
  is not.
- Two pre-existing, VTK-unrelated build messages: `ERROR: Hidden import 'OCP.TKernel' not found`
  and `ERROR: Hidden import 'cadquery.exporters' not found`. Both were already present in the
  unmodified spec's hiddenimports list (`cadquery.exporters` is an attribute of the `cadquery`
  package object at runtime, not a real importable submodule path — a pre-existing spec quirk, not
  introduced by this evaluation) and did not abort the build; not investigated further as out of
  scope for TE-001.2 (unrelated to VTK).
- One unrelated warning: `WARNING: Hidden import "scipy.special._cdflib" not found!` — also
  pre-existing/unrelated to VTK.
- OCP bundled correctly: confirmed in `Bundle-Analysis.md` (78 files, 216.03 MiB in the OCP
  section).
