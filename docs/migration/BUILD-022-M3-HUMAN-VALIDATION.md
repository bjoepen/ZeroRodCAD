# Build 022 M3 — Human Validation Checklist

Same environment limitation as every milestone before it in this series: real interactive WebView
click-through cannot be automated here — macOS Accessibility permission is not granted to this
session (verified directly via `osascript`, not assumed). This checklist is what closes the
remaining gap between "the data pipeline is proven" and "a human actually saw the model rendered
on screen and interacted with it." The Project Owner completed it by hand on 2026-08-09.
**Result: PASS.**

## What automated evidence already covers (not repeated here)

- The real bundled sidecar binary producing a real `zerorod-mesh/v1` payload (`body`, `rod`
  meshes + virtual-string lines), fed through the *actual* `meshContractToGeometries()` frontend
  code — not a synthetic fixture — confirming correct `THREE.BufferGeometry` construction
  (positions, indices, computed normals) from the real payload
  (`mesh.realpayload.test.ts`).
- `fitCameraToBounds` behavior (center, distance scaling, degenerate-bounds safety) — pure-logic
  tests, no renderer needed (`scene.test.ts`).
- `clearGroup` disposing geometry/materials correctly, including multi-material meshes
  (`scene.test.ts`).
- The preview state machine (`idle`/`loading`/`ready`/`error`) and its status/text formatting
  (`preview.test.ts`).
- Mesh payload validation rejecting every malformed shape before it could reach a renderer: wrong
  schema, empty meshes, non-multiple-of-3 arrays, out-of-range indices, NaN/Infinity, missing
  bounds (`mesh.test.ts`).
- 53 frontend tests, 21 Rust tests, 282 Python tests (full repo), all passing.
- The real `.app` launching, its window rendering with the M3 UI (status panel + viewport +
  "Load / Refresh ZeroRod" button) in its correct pre-interaction state, screenshot-verified.
- 0 VTK/PySide6/Qt in the bundle; CSP and WebView capability unchanged from M1/M2; no external CDN
  (Three.js fully bundled locally by Vite).
- Clean app quit, 0 remaining `zerorod-desktop`/`zerorod-engine` processes.

What is **not** automated evidence: actual GPU rasterization (does `WebGLRenderer` paint correct
pixels) and any interactive confirmation (rotate, zoom, resize, refresh-in-a-live-window). That is
exactly what this checklist is for.

## What requires a human clicking the real window

Build (debug) at:

```
desktop/src-tauri/target/debug/bundle/macos/ZeroRodCAD.app
```

Rebuild first if this path is stale — see `docs/migration/BUILD-022-M3-THREEJS-PREVIEW.md`
"Reproducing the build". The app is unsigned; first launch needs the standard Gatekeeper override
(right-click → Open).

## Checklist

- [x] App starts (double-click / `open`, no crash, window appears)
- [x] Engine starts/connects (Python sidecar / CAD engine work)
- [x] Clicking "Load / Refresh ZeroRod" makes a real ZeroRod model become visible in the viewport
- [x] Body geometry is visible and looks plausible
- [x] Rod geometry is visible and looks plausible
- [x] Virtual strings are visible
- [x] Dragging in the viewport rotates the camera around the model (OrbitControls)
- [x] Scrolling/pinching in the viewport zooms in and out
- [ ] The complete model fits inside the initial view — not individually itemized in the tester's
  report; covered generally by "model becomes visible" and "all intended M3 functions work," but
  left unchecked here rather than assumed at this level of detail
- [ ] Resizing the app window resizes the 3D viewport correctly — not individually itemized by the
  tester, left unchecked rather than assumed
- [ ] Clicking "Load / Refresh ZeroRod" again re-loads without needing to restart the app — not
  individually itemized, left unchecked rather than assumed
- [ ] Refresh does not duplicate stale geometry — not individually itemized, left unchecked rather
  than assumed
- [x] No visible renderer errors, no crash, no frozen/unresponsive window (preview "works within
  the implemented M3 scope")
- [ ] App remains responsive throughout — not individually itemized, left unchecked rather than
  assumed
- [ ] Quitting the app closes the window promptly — not individually itemized, left unchecked
  rather than assumed
- [ ] After quitting, no `zerorod-engine` process remains running — not individually itemized,
  left unchecked rather than assumed

The tester's report additionally stated in general terms that "preview funktioniert im
implementierten M3-Scope" and "alle vorgesehenen M3-Funktionen sind gegeben" — a summary
confirmation covering the milestone's scope as a whole. The unchecked items above are left
unchecked because they were not individually itemized in that report, consistent with recording
only what was actually confirmed rather than inferring from a general statement; they do not
change the overall PASS result below, which reflects the tester's own stated verdict.

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Datum | 2026-08-09 |
| macOS Version | not separately recorded by the tester |
| Hardware | not separately recorded by the tester |
| Ergebnis (PASS / FAIL / PARTIAL) | **PASS** |
| Bemerkungen | Human validation completed successfully within the implemented M3 scope. The real ZeroRod preview renders correctly and the interactive view works as intended. |

## Gate BUILD-022-M3

**PASS.** Engineering criteria (`BUILD-022-M3-THREEJS-PREVIEW.md`) PASS + human validation (this
document) PASS. Milestone 3 is COMPLETE.
