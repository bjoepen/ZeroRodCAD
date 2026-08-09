# Build 022 M2 — Human Validation Checklist

Every prior Technology Evaluation in this series (TE-002 through TE-002.2B) hit the same wall in
this environment: real interactive WebView click-through cannot be automated here — macOS
Accessibility permission is not granted to this session, verified directly (`osascript ... click
at {x,y}` fails with `-25211`, "not authorized to send keystrokes"/accessibility), not assumed.
Build 022 M2 hit the identical limitation and closed the gap the same way its predecessors did:
automated evidence covered everything reachable without a human click, and the Project Owner
completed the remaining checklist below by hand on 2026-08-09. **Result: PASS.**

## What automated evidence already covers (not repeated here)

- The exact bundled sidecar binary (`ZeroRodCAD.app/Contents/Resources/zerorod-engine-onedir/zerorod-engine`)
  answering `ping`/`status`/`preview`(×2)/`shutdown` correctly over the real protocol, with
  `vtk_installed: false` and `ocp_variant: cadquery-ocp-novtk` confirmed from inside the frozen
  bundle.
- The same binary, killed with `SIGKILL` mid-session to simulate a crash: confirmed gone
  immediately, no zombie, no orphan — consistent with TE-002.1's onedir-vs-onefile finding.
- Performance: cold start 0.614 s, warm median 0.123 s (`build/reports/build022-m2/persistent-benchmark-2.json`)
  — matches the ~0.612 s / ~0.121 s ADR-022-001 reference baseline.
- 41 Python tests, 21 Rust tests, 17 frontend tests, all passing (`docs/migration/BUILD-022-M2-SIDECAR-LIFECYCLE.md`).
- The app launching for real, its window rendering, and the initial status panel showing the
  correct pre-interaction state (Desktop shell READY, Rust bridge READY with real `app_info` data,
  Python sidecar STOPPED, CAD engine NOT_READY, 3D preview NOT_IMPLEMENTED — screenshot-verified).
- Clean app quit with 0 remaining `zerorod-desktop`/`zerorod-engine` processes (process-list
  checked directly).

## What requires a human clicking the real window

Build (debug) at:

```
desktop/src-tauri/target/debug/bundle/macos/ZeroRodCAD.app
```

Rebuild first if this path is stale: `cd desktop/src-tauri && ../frontend/node_modules/.bin/tauri build --debug`
(needs `desktop/src-tauri/resources/zerorod-engine-onedir/` populated first — see
`docs/migration/BUILD-022-M2-SIDECAR-LIFECYCLE.md` "Reproducing the build").

The app is unsigned; first launch needs the standard Gatekeeper override (right-click → Open).

## Checklist

- [x] App window opens, shows the status panel (five rows) and three buttons: "Start / Check
  Engine", "Ping Engine", "Request Preview Data"
- [x] Initial state / foundation status UI displayed correctly
- [x] Clicking "Start / Check Engine" changes Python sidecar to RUNNING with a pid shown
- [x] Clicking "Ping Engine" changes CAD engine to CONNECTED, showing `cadquery-ocp-novtk` /
  `vtk=False` correctly
- [x] Clicking "Ping Engine" again reuses the already-running persistent sidecar (not restarting
  it — confirmed by the tester as the whole point of persistent + onedir)
- [x] Clicking "Request Preview Data" successfully requests a real mesh; mesh receipt is confirmed
  in the UI — **no 3D model is rendered** (correct for M2; M3's job)
- [x] No visible error message, crash, or frozen window during any of the above
- [x] Quitting the app closes it cleanly
- [ ] No `zerorod-engine` process remains running after quit — not explicitly confirmed by the
  tester's report, so left unchecked rather than assumed (automated evidence already covers this
  for the exact bundled binary; see "What automated evidence already covers" above)

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Datum | 2026-08-09 |
| macOS Version | not separately recorded by the tester |
| Ergebnis (PASS / FAIL / PARTIAL) | **PASS** |
| Bemerkungen | Human validation completed successfully within implemented M2 scope. Engine start, persistent reuse, ping, real preview-mesh request and clean UI operation confirmed. 3D rendering intentionally not part of M2. |

Gate BUILD-022-M2: **PASS** (engineering PASS, recorded in `BUILD-022-M2-SIDECAR-LIFECYCLE.md`, +
this human validation PASS). M2 is COMPLETE.
