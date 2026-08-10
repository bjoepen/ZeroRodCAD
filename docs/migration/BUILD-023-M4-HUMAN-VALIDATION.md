# Build 023 / Milestone 4 — Human Validation Checklist

Engineering completion for M4 (debounced live preview, stale-response protection, coalescing,
camera-preservation heuristic, Apply/Reset integration) is covered by automated evidence: see
`docs/migration/BUILD-023-M4-LIVE-PREVIEW.md` and `scripts/validate-build023-m4.sh`, including a
real request sequence through the freshly rebuilt sidecar proving repeated parameter changes
(`body_width: 38 → 45 → 60 → 38 mm`) all produce correct geometry. This document is the interactive
click-through a human tester still needs to do — how live preview *feels* (debounce timing, camera
behavior while orbiting, absence of flicker) is fundamentally a human judgment call that no unit
test can substitute for, and `createPreviewController` itself is not unit-tested (it constructs a
real `THREE.WebGLRenderer`, which has no GPU context under jsdom).

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

- [ ] App starts normally
- [ ] Default ZeroRod visible
- [ ] Parameter panel usable
- [ ] Change `body_width` 38 → 60
- [ ] Do NOT press Apply
- [ ] After a short pause the model automatically becomes wider
- [ ] Change 60 → 45
- [ ] Model automatically becomes narrower
- [ ] Type quickly through several values
- [ ] Preview does not visibly jump back to older values
- [ ] Final model corresponds to the final entered value
- [ ] Invalid temporary input does not destroy the preview
- [ ] Correcting it resumes automatic preview
- [ ] Domain-invalid value preserves the previous valid model
- [ ] Correcting it recovers automatically
- [ ] Rotate the model
- [ ] Zoom into the model
- [ ] Change a small parameter
- [ ] Camera does not annoyingly reset after every update
- [ ] Orbit controls remain responsive during/after updates
- [ ] Change a string gauge
- [ ] Preview updates automatically
- [ ] Change `project_name`
- [ ] No unnecessary geometry refresh is apparent
- [ ] Reset to Defaults
- [ ] Default geometry returns automatically
- [ ] Apply remains usable and does not cause a duplicate visible refresh
- [ ] Repeated edits remain responsive
- [ ] No visible flicker
- [ ] No blank viewport between updates
- [ ] Errors are understandable
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

## Gate BUILD-023-M4 (human component)

**PENDING.** Engineering criteria are covered by `scripts/validate-build023-m4.sh`; this checklist's
completion is the remaining condition for the milestone's overall PASS. Per the mandate, Claude does
not mark this PASS on its own — only the Project Owner's actual click-through does.
