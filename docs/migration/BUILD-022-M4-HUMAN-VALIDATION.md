# Build 022 M4 — Human Validation Checklist

M4 is primarily a packaging change (dylib deduplication, size reduction) — it does not touch M3's
renderer, M2's sidecar protocol, or the UI. The functional risk surface is therefore narrower than
M2/M3's own checklists, but the same environment limitation applies: real interactive WebView
click-through cannot be automated here (macOS Accessibility permission not granted, verified
directly). This checklist confirms the *optimized* app behaves identically to the already
human-validated M3 build, not that M3's features work at all (that was already confirmed). The
Project Owner completed it by hand on 2026-08-09. **Result: PASS.**

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

- [x] Optimized app starts (double-click / `open`, no crash, window appears)
- [x] Engine starts/connects
- [x] Clicking "Load / Refresh ZeroRod" makes the ZeroRod preview appear
- [x] Body visible and correct
- [x] Rod visible and correct
- [x] Strings visible
- [x] Rotate works
- [x] Zoom works
- [x] Refresh works
- [x] App remains responsive throughout
- [x] Clean quit (no hang)
- [ ] No `zerorod-engine` process remains running after quit — not individually itemized in the
  tester's report, left unchecked rather than assumed (automated evidence already covers this for
  the exact bundled binary; see "What automated evidence already covers" above)

The tester additionally confirmed no functional regression was observed within the implemented M4
scope, consistent with the individual items above.

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Datum | 2026-08-09 |
| macOS Version | not separately recorded by the tester |
| Hardware | not separately recorded by the tester |
| App path | `desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app` |
| App size | 299,066,193 bytes / 285.21 MiB / 299.07 MB / 201 files / 77 symlinks (see `BUILD-022-M4-PRODUCTIVE-PACKAGING.md`) |
| Ergebnis (PASS / FAIL / PARTIAL) | **PASS** |
| Bemerkungen | Human validation of the optimized productive release bundle completed successfully. Application startup, engine connection, ZeroRod preview, rotate, zoom, refresh and clean application operation were confirmed within the implemented Build 022 scope. |

## Gate BUILD-022-M4

**PASS.** Engineering criteria (`BUILD-022-M4-PRODUCTIVE-PACKAGING.md`) PASS + human validation
(this document) PASS. Milestone 4 is COMPLETE.
