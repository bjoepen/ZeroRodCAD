# Build 024 / Milestone 3 — Human Validation Checklist

Engineering completion for M3 (export robustness — post-export verification hardened with a
second, independent Rust-side structural-validation layer; overwrite/TOCTOU behavior
investigated and documented; export retry safety evidence-based decided; real path/Unicode/
spaces/repeated-export/interleaving evidence gathered against the real persistent sidecar) is
covered by automated evidence: see `docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md` and
`scripts/validate-build024-m3.sh`. This document is the interactive click-through a human
tester still needs to do — M3 deliberately does not change the export UI's look or flow from
M2 (Round 2, already Human-Validation-PASS), so this checklist is largely a *regression*
retest plus a few M3-specific additions (Downloads/Documents paths, spaces path), not a new
feature walkthrough.

This environment had no display/GUI access when this checklist was drafted, so every item is
left **unchecked** rather than assumed, per the same allowance used throughout this migration
("Claude leaves unchecked if human clicking unavailable").

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

- [ ] App launches
- [ ] Existing parameter/live preview workflow works
- [ ] Export Model… opens native directory dialog

- [ ] Export to empty directory succeeds
- [ ] STL exists
- [ ] STEP exists
- [ ] report exists
- [ ] exported STL or STEP can be opened externally

- [ ] Export to a directory with spaces in its name succeeds (e.g. create/select a folder
      named "ZeroRod Export Test")
- [ ] Export to a normal `~/Downloads` or `~/Documents` subfolder succeeds

- [ ] Repeat export to same directory
- [ ] overwrite warning appears
- [ ] Cancel preserves existing files
- [ ] Confirm overwrite succeeds

- [ ] Change geometry
- [ ] wait for visible preview
- [ ] export
- [ ] exported model corresponds to visible model

- [ ] Provoke a safe failure if the checklist provides a controlled method (e.g. select a
      destination and revoke write permission via Finder's "Get Info" before exporting, then
      restore it afterward)
- [ ] failure message is understandable
- [ ] next normal export succeeds

- [ ] Preview still rotates/zooms after exports
- [ ] Parameter editing still works
- [ ] App quits cleanly
- [ ] No zerorod-engine process remains after quitting

## Result

| Field | Value |
|---|---|
| Tester | *(pending)* |
| Date | *(pending)* |
| macOS | *(pending)* |
| Hardware | *(pending)* |
| Result | **PENDING** |
| Notes | *(pending — awaiting Project Owner click-through of the fresh M3 release build above)* |

## Gate BUILD-024-M3 (human component)

**PENDING.** The engineering gate (`scripts/validate-build024-m3.sh`) is expected to PASS
independently of this checklist; overall Milestone 3 completion requires both. Per the
mandate's stop condition, M4 does not start until this is complete.
