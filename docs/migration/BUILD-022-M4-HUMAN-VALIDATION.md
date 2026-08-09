# Build 022 M4 — Human Validation Checklist

M4 is primarily a packaging change (dylib deduplication, size reduction) — it does not touch M3's
renderer, M2's sidecar protocol, or the UI. The functional risk surface is therefore narrower than
M2/M3's own checklists, but the same environment limitation applies: real interactive WebView
click-through cannot be automated here (macOS Accessibility permission not granted, verified
directly). This checklist confirms the *optimized* app behaves identically to the already
human-validated M3 build, not that M3's features work at all (that was already confirmed).

## What automated evidence already covers (not repeated here)

- The exact deduplicated bundled sidecar binary answering `ping`/`status`/`preview`(×2)/an
  intentionally invalid command/`shutdown` correctly, including `vtk_installed: false` — both in a
  debug and a release build.
- A real crash simulation (`SIGKILL`) against the deduplicated bundled binary: process gone
  immediately, no zombie — dedup does not affect process-tree/kill behavior.
- Symlink safety: every symlink in the final bundle verified relative, resolving inside the
  bundle, non-broken (no absolute paths, no build-environment leakage).
- Idempotency: a second dedup pass against the already-deduplicated bundle relinks 0 files.
- Performance/memory measured against the deduplicated bundle: no regression vs. M2/M3/TE-002.2B
  baselines.
- 0 VTK/PySide6/Qt/numba/llvmlite/scipy files in the final bundle (both debug and release).
- The real `.app` (release build) launching, window rendering with the correct M3 UI in its
  pre-interaction state, screenshot-verified.
- Clean app quit, 0 remaining `zerorod-desktop`/`zerorod-engine` processes.
- All automated test suites (21 Rust, 41 Python, 53 frontend, 282 full-repo) passing against the
  final packaging configuration.

## What requires a human clicking the real window

Build (release, optimized) at:

```
desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app
```

Rebuild first if this path is stale: `./scripts/build-productive-desktop-app.sh release` (see
`docs/migration/BUILD-022-M4-PRODUCTIVE-PACKAGING.md` "Reproducing the build"). The app is
unsigned; first launch needs the standard Gatekeeper override (right-click → Open).

## Checklist

- [ ] Optimized app starts (double-click / `open`, no crash, window appears)
- [ ] Engine starts/connects ("Start / Check Engine", then "Ping Engine" — Python sidecar RUNNING,
  CAD engine CONNECTED)
- [ ] Clicking "Load / Refresh ZeroRod" makes the ZeroRod preview appear
- [ ] Body visible
- [ ] Rod visible
- [ ] Strings visible
- [ ] Rotate works (OrbitControls drag)
- [ ] Zoom works (scroll/pinch)
- [ ] Refresh works (click "Load / Refresh ZeroRod" again, no stale/duplicated geometry)
- [ ] App remains responsive throughout
- [ ] Clean quit (Cmd+Q or the red close button, no hang)
- [ ] No `zerorod-engine` process remains running after quit (Activity Monitor, or
  `ps aux | grep zerorod-engine` in Terminal, should show nothing)

## Result

| Field | Value |
|---|---|
| Tester | |
| Datum | |
| macOS Version | |
| Hardware | |
| App path | `desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app` |
| App size | ~285 MiB (measured productively — see `BUILD-022-M4-PRODUCTIVE-PACKAGING.md`) |
| Ergebnis (PASS / FAIL / PARTIAL) | |
| Bemerkungen | |

Left intentionally unchecked and unfilled — human tester to complete. Claude does not, and must
not, mark any field above as PASS itself.
