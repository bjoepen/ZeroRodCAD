# Build 025 / Milestone 4 — Human Validation Checklist

Engineering completion for M4 (explicit native macOS Application/File/View menu, native keyboard
shortcuts, native About, and the fix to the M1 Quit-bypass gap) is covered by automated evidence:
see `docs/migration/BUILD-025-M4-DESKTOP-SHELL.md` and `scripts/validate-build025-m4.sh`, including
direct unit coverage of the re-entrancy-safe close/quit dispatcher (`close_flow.test.ts`), the full
menu-id routing table (`native_menu.test.ts`), a real IPC-boundary test of `handle_menu_event`
(`tests/native_menu.rs`), and artifact-level `strings` evidence that the compiled release binary
actually contains the native menu's id/label constants. What automated tests structurally cannot
prove — because real `muda`/AppKit menu *construction* requires the true Cocoa main thread, which
`cargo test`'s harness never runs on (see `BUILD-025-M4-DESKTOP-SHELL.md`'s Testing section) — is
whether the menu looks and behaves right for a human clicking it, and in particular whether native
⌘Q genuinely now goes through the same Save/Discard/Cancel prompt the red close button already
does, across every combination of dirty state. That is what this checklist is for.

**Status: PASS.** Project Owner completed an interactive pass against a freshly built
`ZeroRodCAD-Build025-M4.app` on 2026-08-13 and reported an overall PASS. Per-item checklist
evidence below was not itemized back to this document by the tester; the recorded result is the
reported overall PASS, not a reconstruction of individual checklist ticks.

## Build under test

A fresh, uniquely-named release bundle must be built from this milestone's HEAD via:

```
./scripts/build-productive-desktop-app.sh release
```

then copied to a uniquely-named artifact, e.g.:

```
cp -R "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app" \
      "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD-Build025-M4.app"
```

Exact absolute path, bundle size, and artifact-identity markers are recorded in the final
Abschlussbericht for this milestone, not here (this file is the checklist, not the build record).

Open command:

```
open "<absolute path to ZeroRodCAD-Build025-M4.app>"
```

(Unsigned — first launch needs the standard Gatekeeper override, right-click → Open.)

## Checklist

### Startup

- [ ] App starts normally
- [ ] The application menu bar reads "ZeroRodCAD" (not "zerorod-desktop" or a generic Tauri
      default)
- [ ] Diagnostics (View → Diagnostics) reports Build 025 / M4 — not M1/M2/M3

### File Menu

- [ ] Menu bar shows exactly: New, Open, — , Save, Save As, — , Export Model…
- [ ] New behaves identically to the visible New control
- [ ] Open behaves identically to the visible Open control
- [ ] Save behaves identically to the visible Save control (including no-op when there is nothing
      to save, same as the visible button's disabled state)
- [ ] Save As behaves identically to the visible Save As control
- [ ] Export Model… behaves identically to the visible Export control

### Shortcuts

- [ ] ⌘N triggers New
- [ ] ⌘O triggers Open
- [ ] ⌘S triggers Save
- [ ] ⇧⌘S triggers Save As
- [ ] Shortcuts still work whether focus is on the 3D view or a parameter field (no dead zone)
- [ ] No double-trigger (each shortcut fires its action exactly once, not twice)

### View Menu

- [ ] Menu bar shows exactly: Reset View, — , Show Body, Show Rod, Show Strings, — , Instrument
      Report, Diagnostics
- [ ] Reset View behaves identically to the visible Reset View control
- [ ] Show Body checkmark starts checked; unchecking it hides Body in the 3D view AND unchecks the
      visible Body checkbox
- [ ] Show Rod: same, for Rod
- [ ] Show Strings: same, for Strings
- [ ] Toggling a visible checkbox (Body/Rod/Strings) updates the native menu's checkmark to match
- [ ] Combinations behave correctly in both directions (e.g. hide Body via menu, hide Rod via
      visible checkbox — both checkmarks and both visible checkboxes end up correct)
- [ ] Instrument Report via menu opens the same report the visible toggle opens
- [ ] Diagnostics via menu opens the same panel the visible toggle opens

### About

- [ ] ZeroRodCAD → About ZeroRodCAD opens a native About dialog
- [ ] Version/build/milestone shown in About matches Diagnostics exactly (both say Build 025 / M4)

### Red Close — Clean

- [ ] With no unsaved changes, clicking the red close button closes the window immediately, no
      prompt

### Red Close — Dirty

- [ ] With unsaved changes, clicking the red close button shows the Save/Discard/Cancel prompt
- [ ] Cancel leaves the window open, no data lost
- [ ] Discard closes the window without saving
- [ ] Save saves, then closes the window

### ⌘Q — Clean

- [ ] With no unsaved changes, ⌘Q quits immediately, no prompt

### ⌘Q — Dirty, Cancel

- [ ] With unsaved changes, ⌘Q shows the same Save/Discard/Cancel prompt as red close
- [ ] Cancel leaves the app running, window open, no data lost, project still marked dirty

### ⌘Q — Dirty, Discard

- [ ] ⌘Q with unsaved changes → Discard → app quits without saving

### ⌘Q — Dirty, Save

- [ ] ⌘Q with unsaved changes → Save → project saves, then app quits

### ⌘Q — Untitled, Save

- [ ] ⌘Q on a never-saved (untitled) project with unsaved changes → Save → the normal Save As/file
      picker flow appears, completing it saves and then quits

### ⌘Q — Save As Cancel

- [ ] ⌘Q on an untitled dirty project → Save → cancel the file picker → app remains running, no
      partial/corrupt file written, project still marked dirty

### Re-entrancy

- [ ] Pressing ⌘Q twice in quick succession while the prompt is showing does not stack a second
      prompt
- [ ] Clicking red close while a ⌘Q prompt is already showing does not stack a second prompt (and
      vice versa: triggering ⌘Q while a red-close prompt is showing does not stack a second prompt)

### Shutdown

- [ ] After a completed quit (either red close or ⌘Q), no `zerorod-engine` process remains running
      (check with `pgrep -fl zerorod-engine`)
- [ ] No hang, no crash, no visible lifecycle problem on quit

### Regression

- [ ] Project New/Open/Save/Save As (from M1) still work correctly outside of menu/shortcut use
- [ ] Parameter editing and live preview (from M2) are unaffected
- [ ] Reset View, Body/Rod/Strings visibility, and Instrument Report (from M3) are unaffected when
      driven from their original visible controls, not just from the new menu
- [ ] Export Model… (STL/STEP/report.md) still produces correct output

## Result

| Field | Value |
|---|---|
| Tester | Project Owner |
| Date | 2026-08-13 |
| macOS | *(not itemized by tester)* |
| Hardware | *(not itemized by tester)* |
| Result | **PASS** |
| Notes | Overall PASS reported by the Project Owner; individual checklist items above were not returned itemized and are not reconstructed here. |

## Gate BUILD-025-M4 (human component)

**PASS.** The engineering gate (`scripts/validate-build025-m4.sh`,
`BUILD-025-M4 CONSISTENCY GATE: PASS`) covers everything an automated test can reach; this
checklist covered what only a human, on a real launched app, can confirm — in particular the full
⌘Q dirty-state matrix above. Build 025 M4 is COMPLETE: both the engineering gate and this human
validation record a PASS.
