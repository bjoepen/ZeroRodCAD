# TE-002.1 — Results

## Variant comparison matrix

| Metric | A (onefile, one-shot) | B (onedir, one-shot) | C (onefile, persistent) | D (onedir, persistent) |
|---|---|---|---|---|
| Cold start / per-request cost | 15.789 s median (20 runs) | 0.768 s median (20 runs) | 17.305 s (once) | 0.644 s (once) |
| Warm request cost | n/a (no warm state) | n/a | 0.131 s median | 0.129 s median |
| RSS growth (requests 1→20) | n/a (exits each time) | n/a | +848 KB | +1,136 KB |
| Disk footprint | 135.45 MiB, 1 file | 524.74 MiB, 368 files | 135.45 MiB, 1 file | 524.74 MiB, 368 files |
| Forced-kill leaves an orphan process | n/a (short-lived, not force-killed in tests) | n/a | **Yes** (top-level PID kill orphans the forked worker) | No |
| Works when driven from real Rust code (not just shell) | Yes (TE-002) | Yes (`onedir_variant.rs`) | Yes (`persistent.rs`, `cargo test`) | Yes (`persistent.rs` + `onedir_variant.rs`) |
| No-VTK / No-PySide6 | Yes | Yes | Yes | Yes |

Full per-variant numbers: `Performance.md`, `Memory.md`, `Packaging.md`, `Process-Lifecycle.md`.

## No-VTK / No-PySide6 proof (final bundled artifact)

The onedir sidecar binary packaged inside the built test `.app`
(`Contents/Resources/zerorod-engine-onedir/zerorod-engine`) is **byte-identical**
(SHA-256 `51578d00530a9ac1e16539d816dd0967515d47e889ce27de55786852513e9b9e`) to the standalone
`onedir-dist/` build already covered by the runtime trace below — so that trace's evidence applies
directly to the shipped artifact, not just to a separate copy of it.

| Evidence layer | Result |
|---|---|
| Static `find` scan of the entire built `.app` bundle for `vtk`/`IVtk`/`PySide`/`Qt` | 0 matches at any of the four patterns |
| Build 021 M1 runtime trace, real `preview` + `shutdown` round trip against the persistent onedir binary | 1150 python_modules, 42 native_extensions, 0 loaded_libraries, 0 qt_plugins observed; `exit_status: exited`, `exit_code: 0`, `incomplete: false` |
| Real-token `vtk` regex sweep of that trace's evidence | 2 matches, both known false positives: `cadquery.occ_impl.exporters.vtk` (a module legitimately named `vtk.py`, contains no `vtkmodules` import under the TE-001.1 patch) and `tools.poc.novtk.vtk_import_blocker` (our own blocker module) — zero real `vtkmodules.*` hits |
| `pip show vtk` / `pip show PySide6` in the build environment (`.venv-novtk-bundle`) | Neither installed |

## Functional results

| Checkpoint | Result |
|---|---|
| Real ZeroRod model built, all four variants | PASS — matches TE-001/TE-001.1/TE-001.2/TE-002 exactly (720+146 vertices, 710+140 triangles) |
| `persistent` protocol: multiple sequential requests over one process | PASS — 13/13 `pytest tests/poc/tauri/test_sidecar_persistent.py` (10 unit + 3 real-subprocess) |
| `persistent` protocol: malformed JSON / unknown command / invalid schema don't kill the loop | PASS — error isolation confirmed |
| `persistent` protocol: `shutdown` ends the loop cleanly; EOF without `shutdown` also ends it | PASS |
| Rust engine manager: spawn, request, timeout, crash-detect, restart-once, shutdown | PASS — 15/15 unit tests + 2/2 onedir integration tests, 17/17 total `cargo test` |
| Onedir sidecar driven from real Rust `Command`, not just shell | PASS — `onedir_variant.rs`, 2/2 |
| Full app builds via `tauri build` | PASS — real `.app` produced, both externalBin (onefile) and resources (onedir) artifacts present and correctly placed |
| Test app launches, main process runs without crashing | PASS — confirmed via `ps aux` after `open` |
| Bundled onedir sidecar (exact file inside the `.app`, not a separate copy) responds correctly through the full persistent protocol | PASS — `preview` returned 2 real meshes (2160 position floats in the first), `shutdown` returned `ok`, exit code 0, no stderr noise, 0.814 s total (cold start + first request) |
| No orphaned sidecar process after the bundled-binary test | PASS — `ps aux` empty for `zerorod-engine` afterward |
| App-exit cleanup handler (`kill_if_running`) | PASS — app process killed directly, no leftover `zerorod-engine` process |
| Interactive click ("Load / Refresh ZeroRod" inside the real running WebView) | **NOT VERIFIED** — see below |
| Frontend test suite | PASS — 30/30 (`vitest`, 3 files) |
| Existing ZeroRodCAD test suite (regression check) | PASS — 241 passed, 1 pre-existing unrelated skip, 0 new failures |

## Interactive verification — not automatable in this environment

Attempted via `osascript`/System Events UI scripting, same as TE-002's precedent: blocked by
macOS Accessibility permissions in this sandboxed session
(`"osascript hat keine Berechtigung für den Hilfszugriff"`). Not faked, not silently skipped. To
compensate, the bundled sidecar binary was driven directly through the exact same protocol calls
the WebView's `persistent_preview`/`persistent_shutdown` commands make (see the functional-results
table above) — this closes the "does the shipped artifact actually work" question at the process
and protocol level, but not the "does clicking the button in the actual window work end-to-end
through the WebView" question. That remains for `HUMAN-VALIDATION.md`.
