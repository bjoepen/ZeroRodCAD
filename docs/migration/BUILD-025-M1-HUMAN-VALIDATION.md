# Build 025 / Milestone 1 — Human Validation Checklist

Engineering completion for M1 (New/Open/Save/Save As against the existing `.zerorod` format, a
project session model with dirty tracking, and a data-loss-preventing unsaved-changes guard for
New/Open/Quit) is covered by automated evidence: see
`docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md` and `scripts/validate-build025-m1.sh`,
including real sidecar-subprocess and bundled-onedir-binary proof of the save → preview → open →
export sequence. This document is the interactive click-through a human tester still needs to do —
the actual native macOS Open/Save dialogs, the visual unsaved-changes-guard UX, and general "does
this feel right" judgment are not something a unit test (running under jsdom, no real WebView, no
real OS dialog) can substitute for.

**Status: PASS.** The Project Owner's initial round (against the freshly built
`ZeroRodCAD-Build025-M1.app`) found the red-close-button defect recorded in
`docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md`; Human Validation was correctly withheld
pending a fix. After that fix (commit `d3c93b9`) landed on 2026-08-13, a re-validation round
reported an overall PASS before M2 began the same day. This document's PASS was not synchronized
into this file at the time — recorded here retroactively from that reported result. Nothing below
is marked `[x]`, per this project's record-only-what-was-explicitly-reported convention (see the
Result table below).

## Build under test

A fresh, uniquely-named release bundle must be built from this milestone's HEAD via:

```
./scripts/build-productive-desktop-app.sh release
```

then copied to a uniquely-named artifact per the mandate's Artifact Identity Standard (§36/§37),
e.g.:

```
cp -R "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app" \
      "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD-Build025-M1.app"
```

Exact absolute path, bundle size, and artifact-identity markers are recorded in the final
Abschlussbericht for this milestone, not here (this file is the checklist, not the build record).

Open command:

```
open "<absolute path to ZeroRodCAD-Build025-M1.app>"
```

(Unsigned — first launch needs the standard Gatekeeper override, right-click → Open.)

## Checklist

### Launch

- [ ] App starts
- [ ] Existing preview/parameter functionality (rotate, zoom, pan, live preview, export) still
      works exactly as in the Build 024 release

### New

- [ ] "New" control is visible and enabled
- [ ] Clicking New with a clean/untouched project shows no unsaved-changes prompt
- [ ] After New, canonical default parameters are visible in the form
- [ ] After New, the 3D preview matches the default model
- [ ] Project indicator reads "Untitled project" (or equivalent) with no dirty marker

### Save As

- [ ] Clicking "Save As…" opens the native macOS save dialog
- [ ] The dialog is pre-filled with a sensible default filename derived from the project name
- [ ] Choosing a destination and confirming creates a real `.zerorod` file on disk
- [ ] The created file is not empty and is human-readable JSON
- [ ] The project indicator updates to show the new filename, no dirty marker
- [ ] Cancelling the save dialog leaves everything unchanged (no file created, no state change)

### Modify

- [ ] Changing a parameter (e.g. `body_width`) updates the live preview as before
- [ ] After the change settles (Applied/previewed), the project is shown as having unsaved
      changes (dirty indicator appears)

### Save

- [ ] With a current project path already set, clicking "Save" writes to the existing file
      without showing a dialog
- [ ] The dirty indicator disappears after a successful Save
- [ ] Re-opening the saved file (in a text editor or via Open) shows the updated parameter value

### Open

- [ ] Clicking "Open…" opens the native macOS open dialog, filtered to `.zerorod` files
- [ ] Choosing a different, previously-saved `.zerorod` project loads its parameters correctly
- [ ] The 3D preview updates to match the opened project's geometry (not the previous project's)
- [ ] The project indicator shows the newly opened file's name, no dirty marker
- [ ] Cancelling the open dialog leaves the current project completely unchanged

### Unsaved changes — New

- [ ] Modify a parameter (create unsaved changes), then click New
- [ ] A Save / Discard / Cancel prompt appears
- [ ] **Cancel**: the prompt closes, nothing changes, the modified project is still open exactly
      as it was
- [ ] **Discard**: New proceeds, unsaved changes are lost, canonical defaults load
- [ ] **Save**: (if no path yet) the save dialog appears; after saving successfully, New then
      proceeds automatically

### Unsaved changes — Open

- [ ] Modify a parameter, then click Open…
- [ ] A Save / Discard / Cancel prompt appears (before the native open dialog, not after)
- [ ] **Cancel**: the current, modified project is fully retained; no open dialog was shown
- [ ] **Discard**: the native open dialog then appears, and opening proceeds normally
- [ ] **Save then Open**: saves first, then the native open dialog appears and opening proceeds

### Quit — red macOS close button (native window close)

This is the specific control the Project Owner found broken in the prior round (clicking the red
traffic-light button did nothing — the window never closed). Root cause and fix are recorded in
`docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md`.

- [ ] Clean/untouched project — clicking the red close button closes the window immediately, no
      prompt
- [ ] Modify a parameter (create unsaved changes), then click the red close button
- [ ] A Save / Discard / Cancel prompt appears — the app does not quit immediately
- [ ] **Cancel**: the app remains open, fully unchanged, and is still usable afterward (try
      changing a parameter again)
- [ ] **Discard**: the window closes and the app quits
- [ ] **Save**: the app only quits after the save has actually completed successfully — not
      before. If Save is choosing a destination for the first time (Save As), cancelling that
      destination dialog cancels the whole close — the app stays open
- [ ] Simulate a save failure (e.g. point at a location that can't be written) — the window stays
      open and the unsaved changes remain
- [ ] Type an invalid, never-applied value into a parameter field, then click the red close
      button — the same unsaved-changes prompt appears (the uncommitted draft is protected too,
      not just an already-accepted-and-dirty project)
- [ ] After a successful close, no orphaned `zerorod-engine` process is left running (check with
      `pgrep -fl zerorod-engine`)

### Quit — App menu / ⌘Q

**Known, pre-existing gap — not fixed by this corrective task; do not expect a prompt here.**
Tracing the red-button defect found that macOS's default "Quit ZeroRodCAD" menu item (there is no
custom menu yet — Build 025 M4's job) is wired directly to the native AppKit `terminate:` action,
which currently bypasses the app's unsaved-changes guard entirely and quits immediately regardless
of dirty state. This was true before this fix too; it is called out explicitly here so a human
tester doesn't mistake it for a regression, and so it isn't silently forgotten before M4.

- [ ] Quitting via ⌘Q or the App menu's Quit item with NO unsaved changes closes the app
      immediately, with no prompt (expected)
- [ ] Quitting via ⌘Q or the App menu's Quit item WITH unsaved changes currently also closes the
      app immediately, with no prompt and no data-loss warning (expected today — this is the known
      gap above, tracked for Build 025 M4's native-menu work, not a new defect)
- [ ] No orphaned `zerorod-engine` process is left running after ⌘Q either way (the sidecar has its
      own independent stdin-EOF shutdown fallback, so this holds even though the guard is
      bypassed — confirmed directly against a real built `.app` during this fix)

### Invalid draft (§22)

- [ ] Type an invalid value into a parameter field (e.g. a non-numeric `body_width`) without it
      ever being accepted/applied
- [ ] Attempt New, Open, or Quit
- [ ] A warning/prompt still appears (the invalid, unsaved keystroke input is not silently
      discarded without at least a warning), even though the project itself may not show as
      "dirty"

### General

- [ ] No raw error code, JSON, or Python/Rust traceback is ever shown to the user for any project
      operation — only plain-language messages
- [ ] Preview, export, rotate/zoom/pan continue to work normally after any project operation
      (New/Open/Save)
- [ ] App quits cleanly with no orphaned `zerorod-engine` process left running (check with
      `pgrep -fl zerorod-engine` after quitting)

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Date | 2026-08-13 |
| macOS | *(not individually reported)* |
| Result | **PASS** |
| Notes | Initial round found the close-button defect (see `BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md`); re-validation after the fix reported an overall PASS, not itemized against each checklist line above — those are left unchecked rather than retroactively marked. This table was synchronized to that result during Build 025 M5 documentation cleanup. |

## Gate BUILD-025-M1 (human component)

**PASS.** Combined with the engineering gate (`scripts/validate-build025-m1.sh`), Build 025 M1 is
COMPLETE.
