# TE-001.2 — Discovery

Technology Evaluation, branch `spike/te0012-novtk-production-bundle` (from
`spike/te0011-cadquery-novtk-decoupling`). Not a production change, not a Tauri migration, not a
GUI refactor, not a new packaging architecture.

## Research question

Can the existing ZeroRodCAD Desktop app be built with PyInstaller under macOS as a real `.app`
bundle using `cadquery-ocp-novtk` + the TE-001.1 patch, with no VTK in the bundle or at runtime —
and what is the real measured size saving versus the existing VTK-based app?

## Existing macOS packaging architecture

**Spec files**: `packaging/macos/ZeroRodCAD.spec` (release) and `ZeroRodCAD-Debug.spec` (a
string-substitution wrapper around the release spec — `console=True`, different bundle name, no
independent hiddenimports/excludes list). Entry point `src/zerorodcad_desktop/launcher.py`, bundle
id `de.beblog.zerorodcad`, one runtime hook (`packaging/macos/runtime_hook.py`, the Build 021 M1
recorder — reused verbatim, see `docs/research/TE-001-No-VTK/Discovery.md`).

**hiddenimports** (before this evaluation's change): `OCP`, `OCP.BRep`, `OCP.BRepMesh`,
`OCP.STEPControl`, `OCP.StlAPI`, `OCP.TKernel`, `cadquery`, `cadquery.exporters`,
`cadquery.occ_impl`, `casadi`, `vtkmodules.vtkCommonCore`, `vtkmodules.vtkCommonDataModel`.

**excludes** (46 entries): Jupyter/pandas/matplotlib/tkinter/llvmlite/numba plus most PySide6 Qt
submodules ZeroRodCAD doesn't use (Qt3D, Charts, WebEngine, Multimedia, Quick/QML, Sql, Sensors,
etc.). No VTK/OCP/cadquery/casadi/scipy exclusions existed.

No `collect_all`/`collect_submodules`/`collect_dynamic_libs` calls, no custom PyInstaller
import-hooks directory (`hookspath=[]`) — VTK previously entered the bundle purely through the two
explicit `vtkmodules.*` hiddenimports plus PyInstaller's own module-graph analysis following
`cadquery`'s (pre-TE-001.1-patch) unconditional `import vtkmodules` chain.

**Packaging scripts** (`scripts/`): `create_packaging_venv.sh` (builds `.venv-packaging` from
`packaging/macos/requirements-build.txt`: `-e ../..` + `PySide6>=6.7,<7` + `PyInstaller>=6.16,<7`),
`build_macos_app.sh` (drives the actual `pyinstaller` invocation, then chains
`report_macos_bundle.sh` + `report_suspect_dependencies.sh` + `analyze_pyinstaller_build.sh` for a
release build), `verify_macos_app.sh` (7-step check: `--diagnose`, `--startup-test`,
`scripts/verify_preview_engine.py`, `plutil -lint`, bundle report, suspect-dependency report,
manual `open`), `scripts/runtime_import_probe.py` (fixed-list import smoke test — **the one file
that unconditionally assumed `vtkmodules` is present**), `package_macos_release.sh` (zips the
built app).

Headless smoke-test CLI flags already exist on the desktop app itself
(`src/zerorodcad_desktop/app.py`): `--diagnose` (no `QApplication`, just environment/version
report) and `--startup-test` (constructs a real `QApplication`/`MainWindow`, prints `STARTUP_OK`,
closes without entering the event loop — designed for `QT_QPA_PLATFORM=offscreen` use). Both work
identically against the frozen executable. No new GUI automation was built for TE-001.2 — these
existing flags were reused as-is.

## Bundle-analysis tooling (reused, not rebuilt)

`tools/scan_bundle.py <app.app> --output-dir DIR --dead-libraries --macho-dependencies --no-cache`
is the real, current Scanner 2.0 CLI (backed by `src/zerorod_analysis/`). It writes
`scanner2/scanner2-inventory.json` (per-section file counts/sizes: MacOS, Frameworks, Resources,
PlugIns, PySide6, Qt, VTK, OCP, casadi, Python, Executables, Other) plus Mach-O dependency graphs
and a dead-library/bundle-health report. **VTK classification is file-path-segment-based**
(`"vtkmodules" in path.parts`, exact case-folded segment match — `src/zerorod_analysis/scanner/
classification.py`), confirmed by reading the source: it never inspects Python dotted-import
names, so the known TE-001.1 false positive (`cadquery.occ_impl.exporters.vtk`, a legitimately
named, patched, VTK-free-until-called module) cannot trigger it. No new analysis engine was built.

## Baseline decision — historical, not rebuilt

No `.app` bundle currently exists in this repository (`dist/` absent, `build/ZeroRodCAD` only held
stale PyInstaller intermediate artifacts from an earlier session, not a real bundle). Per section 7
of the mandate ("Baseline darf TE-001.2 nicht unnötig eskalieren" / "wenn bereits belastbare
Messwerte existieren: verwenden"), this evaluation uses the existing, twice-reproduced Scanner 2.0
measurement instead of building a second ~900 MiB VTK-based bundle purely for comparison:

- `build/reports/build-019.1-scanner2/scanner2-report.md` and the byte-identical re-run
  `build/reports/build-019.3-m3/scanner2/scanner2-report.md` — **910.51 MiB total**, 1349 files,
  135 directories, corroborated by plain `du -sh` at **912M**
  (`build/reports/sprint3-minimal-runtime-01/bundle-size.txt`).
- Measured against `cadquery==2.8.0`, `cadquery-ocp==7.9.3.1.1`, `vtk==9.6.2`
  (`build/reports/sprint3-minimal-runtime/requirements-freeze.txt`) — **the exact same dependency
  versions** TE-001/TE-001.1/TE-001.2 use, confirmed apples-to-apples, not a version-mismatched
  comparison.
- Labeled **HISTORICAL** throughout this evaluation's docs, never presented as freshly measured.

See `Size-Comparison.md` for the full before/after table.
