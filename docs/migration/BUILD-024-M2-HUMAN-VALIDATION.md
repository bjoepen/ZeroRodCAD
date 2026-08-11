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

## Round 1 — FAIL (real defect found)

The Project Owner tested the first engineering build (commit `1a7e722`, feature commit
`31d1d11`) and found a real, reproducible runtime error:

```text
invalid args `outputDirectory` for command `engine_export_preflight`:
command engine_export_preflight missing required key outputDirectory
```

Additionally reported: a target/Downloads folder could not be correctly selected/used for
export in the real app.

**Root cause and fix**: see `docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md` for the full
record — both symptoms were the same underlying defect (a Tauri IPC argument-name mismatch
between `export.ts`'s `output_directory` payload key and `engine_export`/
`engine_export_preflight`'s default camelCase-only argument binding; the native directory
dialog itself was not defective). Fixed by adding
`#[tauri::command(rename_all = "snake_case")]` to both affected Rust commands, with new
regression tests (`desktop/src-tauri/src/commands.rs`'s `ipc_argument_binding` module) that
dispatch a real IPC request through Tauri's actual command deserializer — verified to
reproduce the exact reported error when the fix is reverted, and to pass once it's applied.
`scripts/validate-build024-m2.sh` itself had a blind spot (nothing in it previously dispatched
a real IPC request through the Rust/Tauri argument-binding layer) — also fixed, documented in
the bugfix record.

| Field | Value |
|---|---|
| Tester | Project Owner |
| Result | **FAIL** |
| Defect | `engine_export_preflight` (and, by identical construction, `engine_export`) rejected the real frontend payload — `outputDirectory` argument-binding mismatch |
| Fix record | `docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md` |

## Round 2 — retest (this checklist, reset to PENDING)

This environment had no display/GUI access when this checklist was drafted or updated, so
every item below is left **unchecked** rather than assumed, per the same allowance Build
023's own human validation documents used ("Claude leaves unchecked if human clicking
unavailable"). The fix is not assumed to make the flow work end to end from a human's
perspective — only a real re-test can confirm that.

## Build under test

A fresh release bundle was built from the corrected M2 HEAD via:

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

Regression items for the specific reported defect, first:

- [ ] Export Model… opens native directory dialog
- [ ] A normal directory can be selected (try `~/Downloads` or `~/Documents` specifically —
      the originally reported case)
- [ ] Selected directory is accepted
- [ ] No `outputDirectory`/`output_directory` argument error occurs
- [ ] Export completes
- [ ] STL exists
- [ ] STEP exists
- [ ] report exists
- [ ] overwrite warning works
- [ ] cancel works
- [ ] preview remains functional
- [ ] app quits cleanly

Full checklist:

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

- [ ] Select an empty destination (try a normal user folder such as `~/Downloads` or
      `~/Documents`, or an engineering-safe subfolder of one — the originally reported case)
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
| Notes | *(pending — awaiting Project Owner re-test of the corrected release build above; Round 1's specific failure is not assumed fixed from engineering evidence alone)* |

## Gate BUILD-024-M2 (human component)

**PENDING** (Round 2). Round 1 was **FAIL** — see above. The engineering gate
(`scripts/validate-build024-m2.sh`) re-passes after the fix, including new regression
coverage for the exact defect class found; overall Milestone 2 completion still requires a
real human re-test to PASS.
