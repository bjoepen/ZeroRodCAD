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

## Round 2 — PASS

The Project Owner re-tested the corrected build and confirmed: native directory selection
works, export succeeds, STL/STEP/report are generated, and the exported model can be opened
successfully — exactly the sequence Round 1 broke on. This confirmation was reported directly
(not observed interactively by Claude — no display/GUI access exists in this environment), so
only the specific checklist items with a clear, direct match to what was reported are marked
`[x]` below; items not explicitly covered by that report are left unchecked rather than
assumed, even where plausibly implied — the same discipline
`BUILD-023-M4-HUMAN-VALIDATION.md` already established for this migration. No repeat
validation was performed by Claude to produce this update.

| Field | Value |
|---|---|
| Tester | Project Owner |
| Result | **PASS** |
| Notes | Native directory selection works; export succeeds; STL/STEP/report are generated; the exported model can be opened successfully. Confirms the Round 1 `outputDirectory` defect is resolved. |

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

- [x] Export Model… opens native directory dialog
- [x] A normal directory can be selected (try `~/Downloads` or `~/Documents` specifically —
      the originally reported case)
- [x] Selected directory is accepted
- [x] No `outputDirectory`/`output_directory` argument error occurs
- [x] Export completes
- [x] STL exists
- [x] STEP exists
- [x] report exists
- [ ] overwrite warning works
- [ ] cancel works
- [ ] preview remains functional
- [ ] app quits cleanly

Full checklist:

- [x] App starts
- [ ] Current ZeroRod visible
- [ ] Parameters/live preview still work
- [ ] Export control visible
- [ ] Export control wording understandable

- [x] Click Export
- [x] Native macOS directory dialog opens
- [x] Dialog allows directory selection
- [ ] Cancel closes dialog cleanly
- [ ] Cancel produces no error

- [x] Select an empty destination (try a normal user folder such as `~/Downloads` or
      `~/Documents`, or an engineering-safe subfolder of one — the originally reported case)
- [x] Export completes
- [ ] Success state appears
- [x] STL file exists
- [x] STEP file exists
- [x] Markdown report exists

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
| Tester | Project Owner |
| Date | *(not separately itemized by the tester's report)* |
| macOS | *(not separately itemized by the tester's report)* |
| Hardware | *(not separately itemized by the tester's report)* |
| Result | **PASS** (Round 2) |
| Notes | Native directory selection works, export succeeds, STL/STEP/report are generated, and the exported model opens successfully. Items above with a clear, direct match to this report are marked `[x]`; items not explicitly covered (overwrite flow, cancellation, project_name edge cases, live-preview-pending behavior, quit/orphan cleanup) are left unchecked rather than assumed. |

## Gate BUILD-024-M2 (human component)

**PASS** (Round 2), as reported by the Project Owner. Round 1 was **FAIL** — see above; the
underlying defect is fixed and re-confirmed working end to end. Combined with the engineering
gate (`scripts/validate-build024-m2.sh`, PASS), **Gate BUILD-024-M2: PASS** overall — Milestone
2 is COMPLETE.
