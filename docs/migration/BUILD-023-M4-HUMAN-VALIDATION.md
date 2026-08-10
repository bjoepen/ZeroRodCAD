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

This environment had no display/GUI access when the checklist below was drafted, so every item was
initially left **unchecked** rather than assumed, per the mandate's own allowance for this ("Claude
leaves unchecked if human clicking unavailable").

**Update (2026-08-10):** the Project Owner has since performed this validation against the fresh
release bundle built for M4 (`docs/migration/BUILD-023-M4-LIVE-PREVIEW.md`'s artifact, commit
`46a0922`) and reported specific confirmed behaviors (see "Result" below). Checklist items with a
clear, direct match to what was actually reported are marked `[x]`; items not explicitly covered by
that report are left unchecked rather than assumed, even where plausibly implied — no additional or
repeat validation was performed by Claude to produce this update.

## Build under test

A fresh release bundle was built from this milestone's exact HEAD (see the final report for the
commit and absolute path) via:

```
./scripts/build-productive-desktop-app.sh release
```

then open the reported `ZeroRodCAD.app` path (unsigned — first launch needs the standard Gatekeeper
override, right-click → Open).

## Checklist

- [x] App starts normally
- [x] Default ZeroRod visible
- [x] Parameter panel usable
- [x] Change `body_width` 38 → 60
- [ ] Do NOT press Apply
- [x] After a short pause the model automatically becomes wider
- [ ] Change 60 → 45
- [ ] Model automatically becomes narrower
- [x] Type quickly through several values
- [x] Preview does not visibly jump back to older values
- [ ] Final model corresponds to the final entered value
- [x] Invalid temporary input does not destroy the preview
- [x] Correcting it resumes automatic preview
- [ ] Domain-invalid value preserves the previous valid model
- [ ] Correcting it recovers automatically
- [x] Rotate the model
- [x] Zoom into the model
- [ ] Change a small parameter
- [x] Camera does not annoyingly reset after every update
- [x] Orbit controls remain responsive during/after updates
- [ ] Change a string gauge
- [ ] Preview updates automatically
- [ ] Change `project_name`
- [ ] No unnecessary geometry refresh is apparent
- [x] Reset to Defaults
- [x] Default geometry returns automatically
- [ ] Apply remains usable and does not cause a duplicate visible refresh
- [x] Repeated edits remain responsive
- [ ] No visible flicker
- [ ] No blank viewport between updates
- [ ] Errors are understandable
- [ ] App quits cleanly

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Date | 2026-08-10 |
| macOS | not separately itemized by the tester's report |
| Hardware | not separately itemized by the tester's report |
| Result | **PASS** |
| Notes | Human validation completed successfully. Live preview updates the real model according to edited values. Rapid edits, invalid-input recovery, preview stability, camera/orbit usability and normal application operation were validated within the implemented Build 023 M4 scope. |

## Gate BUILD-023-M4 (human component)

**PASS**, as reported by the Project Owner. Combined with the engineering gate
(`scripts/validate-build023-m4.sh`, PASS), **Gate BUILD-023-M4: PASS** overall — Milestone 4 is
COMPLETE.
