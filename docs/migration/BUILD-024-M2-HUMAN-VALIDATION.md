# Build 024 / Milestone 2 — Human Validation Checklist

Engineering completion for M2 (native directory dialog wired into a real Export UI trigger,
overwrite preflight/confirmation, export state machine, structured error presentation) is
covered by automated evidence: see `docs/migration/BUILD-024-M2-EXPORT-CONTROLS.md` and
`scripts/validate-build024-m2.sh`, including a real request sequence through the freshly
rebuilt sidecar proving the full preview → preflight → export → preflight (conflict) →
export (overwrite) → preview → shutdown flow. This document is the interactive click-through
a human tester still needs to do — the actual native macOS directory dialog, the visual
overwrite-confirmation UX, and general "does this feel right" judgment are not something a
unit test (running under jsdom, no real WebView, no real OS dialog) can substitute for.

This environment had no display/GUI access when this checklist was drafted, so every item is
left **unchecked** rather than assumed, per the same allowance Build 023's own human
validation documents used ("Claude leaves unchecked if human clicking unavailable").

## Build under test

A fresh release bundle was built from this milestone's exact HEAD via:

```
./scripts/build-productive-desktop-app.sh release
```

Absolute path (see the final report for the exact commit this was built from):

```
/Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app
```

Open command:

```
open "/Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
```

(Unsigned — first launch needs the standard Gatekeeper override, right-click → Open.)

## Checklist

- [ ] App starts
- [ ] Current ZeroRod visible
- [ ] Parameters/live preview still work
- [ ] Export control visible
- [ ] Export control wording understandable

- [ ] Click Export
- [ ] Native macOS directory dialog opens
- [ ] Dialog allows directory selection
- [ ] Cancel closes dialog cleanly
- [ ] Cancel produces no error

- [ ] Select an empty destination
- [ ] Export completes
- [ ] Success state appears
- [ ] STL file exists
- [ ] STEP file exists
- [ ] Markdown report exists

- [ ] Generated filenames are understandable
- [ ] Exported model corresponds to currently visible model

- [ ] Change body_width
- [ ] Wait for live preview
- [ ] Export again to a different empty directory
- [ ] Exported model corresponds to changed geometry

- [ ] Export to directory containing same outputs
- [ ] Overwrite warning appears
- [ ] Cancel overwrite
- [ ] Existing files remain untouched

- [ ] Repeat and confirm overwrite
- [ ] Export succeeds

- [ ] Change project_name
- [ ] Export filenames follow expected sanitized project name

- [ ] Export while live preview is pending
- [ ] UI behavior matches documented stable-export rule (trigger disabled until preview settles)

- [ ] No raw traceback appears
- [ ] App remains responsive
- [ ] Preview still works after export
- [ ] Rotate/zoom still work
- [ ] App quits cleanly
- [ ] No zerorod-engine process remains

## Result

| Field | Value |
|---|---|
| Tester | *(pending)* |
| Date | *(pending)* |
| macOS | *(pending)* |
| Hardware | *(pending)* |
| Result | **PENDING** |
| Notes | *(pending — awaiting Project Owner click-through of the fresh release build above)* |

## Gate BUILD-024-M2 (human component)

**PENDING.** The engineering gate (`scripts/validate-build024-m2.sh`) is expected to PASS
independently of this checklist; overall Milestone 2 completion requires both.
