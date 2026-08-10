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
| Tester | *(pending)* |
| Date | *(pending)* |
| macOS | *(pending)* |
| Hardware | *(pending)* |
| Result | **PENDING** |
| Notes | Not yet performed — no interactive display available in the environment this milestone was engineered in. |

## Gate BUILD-023-M3 (human component)

**PENDING.** Engineering criteria are covered by `scripts/validate-build023-m3.sh`; this checklist's
completion is the remaining condition for the milestone's overall PASS. Per the mandate, Claude does
not mark this PASS on its own — only the Project Owner's actual click-through does.
