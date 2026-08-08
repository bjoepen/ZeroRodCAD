# TE-001.2 — Runtime Validation

All checks below were run against the actual built `dist/ZeroRodCAD Desktop.app`, not source-level
approximations, unless explicitly marked otherwise.

## Startup (section 14)

```
"$APP/Contents/MacOS/ZeroRodCAD Desktop" --diagnose
```
```
[OK] Platform: macOS-26.5.2-arm64-arm-64bit-Mach-O
[OK] Machine: arm64
[OK] Python: 3.13.14
[OK] Frozen application: yes
[OK] CadQuery: 2.8.0
[OK] PySide6: not installed          <- see note below
[OK] Writable home directory: /Users/bernd
```

```
QT_QPA_PLATFORM=offscreen "$APP/Contents/MacOS/ZeroRodCAD Desktop" --startup-test
```
```
STARTUP_OK
Log: /Users/bernd/Library/Logs/ZeroRodCAD/zerorodcad.log
```
Exit code 0. No VTK import exception, no OCP load exception, no PySide6 regression — a real
`QApplication`/`MainWindow` were constructed successfully (the `--startup-test` code path requires
this).

Additionally, the app was launched **without** `QT_QPA_PLATFORM=offscreen` (`open "dist/ZeroRodCAD
Desktop.app"`) — a real on-screen window appeared (confirmed via `osascript`'s System Events
process list showing `ZeroRodCAD Desktop` as a foreground process), ran without crashing, and was
quit cleanly. An automated screenshot (`screencapture`) was attempted for pixel-level visual
confirmation but failed in this environment (`could not create image from display` — a
screen-recording permission constraint of this sandboxed session, not an app defect). Per the
mandate's explicit instruction not to fake visual verification: this specific pixel-level check is
marked **NOT VERIFIED**, while the broader "process launches, window appears, no crash, clean
quit" result is **AUTOMATED** (confirmed via process listing, not assumed).

**Note on the `--diagnose` "PySide6: not installed" line**: PySide6 is demonstrably installed and
working (the whole GUI/startup-test path depends on it and succeeded). This is a pre-existing
display quirk in `zerorodcad_desktop/diagnostics.py` — most likely `importlib.metadata.version
("PySide6")` failing because PyInstaller does not bundle `.dist-info` metadata for hidden-imported
packages by default. Not touched or introduced by this evaluation (nothing about VTK removal
affects PySide6 metadata bundling); noted here for completeness, not treated as a Gate C blocker
since the actual PySide6 functionality works.

## Preview (section 15)

Reused the Build 021 M1 runtime-trace stimulus mechanism already baked into
`packaging/macos/runtime_hook.py` (`PROFILE_PREVIEW_PROBE`) — no new GUI automation built.

```
QT_QPA_PLATFORM=offscreen \
ZEROROD_RUNTIME_TRACE=1 ZEROROD_RUNTIME_TRACE_PROFILE=preview-probe \
ZEROROD_RUNTIME_TRACE_RAW_PATH=<path> ZEROROD_RUNTIME_TRACE_BUNDLE_ROOT=<app path> \
"$EXE" --startup-test
```
Raw trace confirms `{"event": "stimulus-complete", "profile": "preview-probe"}` — i.e.
`zerorodcad.preview.build_preview_scene(ZeroRodParameters())` ran inside the frozen bundle and
returned non-empty meshes (the stimulus asserts this itself; a `recorder-error` event would have
been written otherwise — none was).

Classification: **AUTOMATED** (mesh generation, no exception) for the PreviewMesh/
`build_preview_scene()` contract that `zerorodcad_desktop/preview_widget.py` actually renders from.
Pixel-level "does it look right on screen" is **NOT VERIFIED**, same screen-recording-permission
constraint as above — not faked.

## Bundled STL export (section 16)

Same mechanism, `PROFILE_EXPORT_PROBE`, writing into a stimulus directory:

```
ZEROROD_RUNTIME_TRACE_PROFILE=export-probe ZEROROD_RUNTIME_TRACE_STIMULUS_DIR=<dir> ...
```

Result: `cbg-open-g-body.stl`, **116984 bytes** — file exists, non-empty, plausible size,
**byte-identical** to the STL produced by TE-001/TE-001.1's source-level (non-bundled) checkpoint
runs. `{"event": "stimulus-complete", "profile": "export-probe"}` confirms no exception.

## Bundled STEP export (section 17)

Same run: `cbg-open-g-assembly.step`, **105003 bytes** — file exists, non-empty, plausible size,
**byte-identical** to TE-001/TE-001.1's source-level STEP output.

## Runtime trace (section 18, Build 021 M1 reused, not duplicated)

Both the preview-probe and export-probe raw traces were converted to proper `RuntimeTrace` objects
via `tools/poc/novtk/runtime_trace_adapter.py` (same adapter TE-001/TE-001.1 used) and checked with
the corrected `vtk_evidence()` heuristic:

| Profile | python_modules | native_extensions | loaded_libraries | `vtk_evidence()` |
|---|---:|---:|---:|---|
| preview-probe | 1098 | 43 | 0 | `[]` |
| export-probe | (recorded) | (recorded) | (recorded) | `[]` |

Both traces: `incomplete: False`, `error: None`. Zero real VTK evidence in either profile. The
`cadquery.occ_impl.exporters.vtk` module *is* observed in the raw audit trail (it gets imported as
part of the patched `cadquery.occ_impl.exporters` package init) — correctly excluded from
`vtk_evidence()`'s results by the file-path-segment / dotted-module-root logic, exactly as designed
in TE-001.1 and re-verified here against the frozen bundle's actual runtime behavior, not just the
bare-venv case TE-001.1 tested.

## OS-level check (section 19)

The app was launched for real (`QT_QPA_PLATFORM=offscreen`, real process, real event loop — not
`--startup-test`), given 3 seconds to fully initialize, then inspected live before being
terminated:

```
lsof -p <PID>    → 191 lines
vmmap <PID>      → 4305 lines
```

Both scanned with the same real-token regex `(?<!no)vtk` (case-insensitive, excludes the "novtk"
substring from `.venv-novtk-bundle`'s own path — the same false-positive fix from TE-001/TE-001.1)
via a direct Python check against the captured output:

```
lsof-output.txt  → 0 real vtk hits
vmmap-output.txt → 0 real vtk hits
```

**Both tools ran successfully — not `NOT VERIFIED`.** Zero VTK mappings found in the live,
running, frozen bundle process.

## Summary against Gate C's functional criteria

| Requirement | Result |
|---|---|
| App startet | PASS (`--diagnose`, `--startup-test`, and a real on-screen launch all succeeded) |
| Geometry funktioniert | PASS (export-probe/STEP path exercises `build_assembly`; byte-identical output to source-level tests) |
| PreviewMesh funktioniert | PASS (preview-probe stimulus-complete, non-empty meshes) |
| bestehende Preview funktioniert oder nachvollziehbar validiert | PASS at the mesh-generation contract level (AUTOMATED); pixel-level rendering NOT VERIFIED (permission-constrained, honestly disclosed, not faked) |
| STL funktioniert | PASS (116984 bytes, byte-identical to source-level) |
| STEP funktioniert | PASS (105003 bytes, byte-identical to source-level) |
| Runtime Trace beobachtet kein VTK | PASS (both profiles, `vtk_evidence()` → `[]`) |
| OS-Level beobachtet kein VTK | PASS (`lsof`/`vmmap`, both tools succeeded, 0 real hits) |
