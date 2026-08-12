# Build 023 / Milestone 3 — Human Validation Checklist

Engineering completion for M3 (Apply connected to the real engine, atomic preview replacement,
accepted/dirty state model, metadata-only-Apply optimization, no automatic regeneration) is covered
by automated evidence: see `docs/migration/BUILD-023-M3-PARAMETER-ENGINE-INTEGRATION.md` and
`scripts/validate-build023-m3.sh`, including a real request through the freshly rebuilt sidecar
proving `body_width: 38 → 60 mm` actually changes the returned mesh's X extent. This document is the
interactive click-through a human tester still needs to do — seeing the actual Three.js viewport
change shape, real keyboard/mouse interaction with Apply, and camera/OrbitControls behavior after a
live regeneration cannot be fully proven by jsdom-based unit tests alone (`createPreviewController`
itself is not unit-tested — it constructs a real `THREE.WebGLRenderer`, which has no GPU context
under jsdom).

This environment has no display/GUI access, so every item below is left **unchecked** rather than
assumed, per the mandate's own allowance for this ("Claude leaves unchecked if human clicking
unavailable").

## Build under test

A fresh release bundle was built from this milestone's exact HEAD (see the final report for the
commit and absolute path) via:

```
./scripts/build-productive-desktop-app.sh release
```

then open the reported `ZeroRodCAD.app` path (unsigned — first launch needs the standard Gatekeeper
override, right-click → Open).

## Checklist

- [ ] App launches normally
- [ ] Parameter panel visible
- [ ] Existing default ZeroRod renders
- [ ] Change `body_width` from default to 60 mm
- [ ] Preview does NOT change before Apply
- [ ] Dirty/modified state appears
- [ ] Press Apply
- [ ] Applying state appears briefly/appropriately
- [ ] Preview visibly becomes wider
- [ ] Dirty state clears after success
- [ ] Rotate still works
- [ ] Zoom still works
- [ ] Change `body_width` again
- [ ] Apply again
- [ ] Preview changes again
- [ ] Enter an invalid value
- [ ] Apply is blocked or error shown appropriately
- [ ] Existing preview remains visible
- [ ] Correct invalid value
- [ ] Error clears
- [ ] Reset to Defaults
- [ ] Preview does NOT immediately change
- [ ] Dirty state reflects reset draft vs. applied state
- [ ] Press Apply
- [ ] Default geometry returns
- [ ] Gauge editing remains usable
- [ ] `project_name` editing remains usable
- [ ] App remains responsive
- [ ] App quits cleanly

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Date | not separately itemized by the tester's report |
| macOS | not separately itemized by the tester's report |
| Hardware | not separately itemized by the tester's report |
| Result | **PASS** |
| Notes | Reported directly by the Project Owner: "Eingegebene Werte verändern das reale ZeroRod-Modell entsprechend den Erwartungen" — entered values change the real ZeroRod model as expected. This confirms the complete manual productive path (parameter edit → local draft validation → Apply → `zerorod-parameters/v1` → Rust → persistent Python sidecar → ZeroRodCAD/CadQuery → `zerorod-mesh/v1` → Three.js → visibly changed geometry). Individual checklist rows above were not itemized in that report and are left unchecked rather than retroactively assumed — the aggregate PASS in this table is the actual recorded result. No additional or repeat validation was performed by Claude to produce this update. |

## Gate BUILD-023-M3 (human component)

**PASS**, as reported by the Project Owner. Combined with the engineering gate
(`scripts/validate-build023-m3.sh`, PASS), **Gate BUILD-023-M3: PASS** overall — Milestone 3 is
COMPLETE.
