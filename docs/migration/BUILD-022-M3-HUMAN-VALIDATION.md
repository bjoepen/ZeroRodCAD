# Build 022 M3 — Human Validation Checklist

Same environment limitation as every milestone before it in this series: real interactive WebView
click-through cannot be automated here — macOS Accessibility permission is not granted to this
session (verified directly via `osascript`, not assumed). This checklist is what closes the
remaining gap between "the data pipeline is proven" and "a human actually saw the model rendered
on screen and interacted with it."

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

- [ ] App starts (double-click / `open`, no crash, window appears)
- [ ] Engine starts/connects (click "Start / Check Engine", then "Ping Engine" — Python sidecar
  shows RUNNING, CAD engine shows CONNECTED)
- [ ] Clicking "Load / Refresh ZeroRod" makes a ZeroRod model become visible in the viewport
- [ ] Body geometry is visible and looks plausible (not garbled, not blank)
- [ ] Rod geometry is visible and looks plausible
- [ ] Virtual strings are visible (distinct from the solid meshes — thin lines, not triangles)
- [ ] The complete model fits inside the initial view (no part cut off, not zoomed in past the
  model, not a tiny speck in the middle of an empty viewport)
- [ ] Dragging in the viewport rotates the camera around the model (OrbitControls)
- [ ] Scrolling/pinching in the viewport zooms in and out
- [ ] Resizing the app window resizes the 3D viewport correctly (no stretching, no stale canvas
  size, no blank strip)
- [ ] Clicking "Load / Refresh ZeroRod" again re-loads without needing to restart the app
- [ ] Refresh does not duplicate stale geometry (no doubled/ghosted model, no leftover geometry
  from the previous load visible alongside the new one)
- [ ] No visible renderer errors, no crash, no frozen/unresponsive window during any of the above
- [ ] App remains responsive throughout (buttons still clickable, viewport still interactive)
- [ ] Quitting the app (Cmd+Q or the red close button) closes the window promptly, without a hang
- [ ] After quitting, no `zerorod-engine` process remains running (Activity Monitor, or
  `ps aux | grep zerorod-engine` in Terminal, should show nothing)

## Result

| Field | Value |
|---|---|
| Tester | |
| Datum | |
| macOS Version | |
| Hardware | |
| Ergebnis (PASS / FAIL / PARTIAL) | |
| Bemerkungen | |

Left intentionally unchecked and unfilled — human tester to complete. Claude does not, and must
not, mark any field above as PASS itself.
