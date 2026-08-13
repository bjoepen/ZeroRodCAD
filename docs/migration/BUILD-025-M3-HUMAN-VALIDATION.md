# Build 025 / Milestone 3 — Human Validation Checklist

Engineering completion for M3 (Reset View, Body/Rod/Strings visibility, the in-app Instrument
Report, and the build-identity correction to 025/M3) is covered by automated evidence: see
`docs/migration/BUILD-025-M3-PREVIEW-REPORT-PARITY.md` and `scripts/validate-build025-m3.sh`,
including a real bundled-onedir-binary smoke sequence exercising `parameters_defaults` → `preview`
→ `report` (default and alternate geometry) → `export` → `shutdown` on the same persistent sidecar
process, and a report/export semantic-consistency test across three parameter scenarios. This
document is the interactive click-through a human tester still needs to do — how Reset View
actually feels, whether the Instrument Report reads well, and general "does this feel right"
judgment are not something a unit test (running under jsdom, no real WebView, no real GPU) can
substitute for.

**Status: PENDING.** No human validation has been performed yet. Nothing below is marked `[x]`.

## Build under test

A fresh, uniquely-named release bundle must be built from this milestone's HEAD via:

```
./scripts/build-productive-desktop-app.sh release
```

then copied to a uniquely-named artifact, e.g.:

```
cp -R "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app" \
      "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD-Build025-M3.app"
```

Exact absolute path, bundle size, and artifact-identity markers are recorded in the final
Abschlussbericht for this milestone, not here (this file is the checklist, not the build record).

Open command:

```
open "<absolute path to ZeroRodCAD-Build025-M3.app>"
```

(Unsigned — first launch needs the standard Gatekeeper override, right-click → Open.)

## Checklist

### Startup

- [ ] App starts normally
- [ ] ZeroRod appears automatically
- [ ] No engine/debug interaction required

### View

- [ ] Fit View works
- [ ] Reset View works, if separately implemented (this build implements exactly one control,
      "Reset View" — see `BUILD-025-M3-PREVIEW-REPORT-PARITY.md` for the legacy-parity discovery
      this is based on)
- [ ] Rotate works
- [ ] Zoom works
- [ ] Pan works

### Visibility

- [ ] Body can be hidden
- [ ] Body can be shown
- [ ] Rod can be hidden
- [ ] Rod can be shown
- [ ] Strings can be hidden
- [ ] Strings can be shown
- [ ] Combinations behave correctly (e.g. Body + Strings hidden, only Rod visible)
- [ ] Visibility survives a parameter/live-preview change (hide Body, edit a parameter, Body
      remains hidden after the preview updates)
- [ ] Reset View, with a layer hidden, frames only the currently visible geometry

### Instrument Report

- [ ] Report opens
- [ ] Report is readable (real headings/tables, not a raw text/JSON dump)
- [ ] Report describes the current accepted model
- [ ] A parameter change is reflected in the report after the live preview accepts it
- [ ] While a draft edit is temporarily invalid, the report continues to describe the last
      accepted model (does not go blank or error)
- [ ] Report does not expose raw debug/traceback data

### Project

- [ ] New
- [ ] Open
- [ ] Save
- [ ] Save As
- [ ] Presentation-only view changes (visibility, Reset View) do NOT mark the project dirty
- [ ] Dirty guard (Save/Discard/Cancel) still works for actual parameter changes
- [ ] Red close button still works (clean close, dirty guard, Cancel/Discard/Save)

### Export

- [ ] "Export Model…" works
- [ ] STL opens
- [ ] STEP opens
- [ ] `report.md` exists and its content matches what the in-app Instrument Report showed for the
      same accepted state

### Diagnostics

- [ ] Still available
- [ ] Remains optional — the app works fully without ever opening it
- [ ] Still contains only technical information (Reset View/visibility/Report are NOT there)

### Shutdown

- [ ] Red close exits the app
- [ ] No visible lifecycle problem (no hang, no crash)
- [ ] No `zerorod-engine` process remains running after quit (check with `pgrep -fl zerorod-engine`)

### Known Limitation

- [ ] The implicit macOS Quit/⌘Q guard bypass remains documented for M4 — confirm it behaves the
      same as in M1/M2 (quits immediately, no prompt, regardless of unsaved changes); this is a
      known, pre-existing limitation, not a new M3 regression, and is explicitly **not** to be
      fixed during this validation pass.

## Result

| Field | Value |
|---|---|
| Tester | *(Project Owner — not yet performed)* |
| Date | *(pending)* |
| macOS | *(pending)* |
| Hardware | *(pending)* |
| Result | **PENDING** |
| Notes | — |

## Gate BUILD-025-M3 (human component)

**PENDING.** Engineering gate (`scripts/validate-build025-m3.sh`) result is recorded separately in
the milestone's final Abschlussbericht. Engineering PASS does not by itself constitute
`BUILD-025-M3 CONSISTENCY GATE: PASS` for product purposes until this human validation is also
complete — Build 025 M4 is not authorized to start before then.
