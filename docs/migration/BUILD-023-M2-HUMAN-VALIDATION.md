# Build 023 / Milestone 2 — Human Validation Checklist

Engineering completion for M2 (parameter panel, defaults loading, local draft/dirty/reset state,
local validation feedback, no automatic preview regeneration) is covered by automated evidence: see
`docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md` and `scripts/validate-build023-m2.sh`. This
document is the interactive click-through a human tester still needs to do — real WebView keyboard
input, focus behavior, and visual layout cannot be fully proven by jsdom-based unit tests alone.

This environment has no display/GUI access, so every item below is left **unchecked** rather than
assumed, per the mandate's own allowance for this ("Claude leaves unchecked if human clicking
unavailable").

## Build under test

```
./scripts/build-productive-desktop-app.sh release
```

then open:

```
desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app
```

(unsigned — first launch needs the standard Gatekeeper override, right-click → Open), or run
`npm run dev` in `desktop/frontend` together with `cargo tauri dev` in `desktop/src-tauri` for a dev
build.

## Checklist

- [ ] App starts
- [ ] Parameter panel visible
- [ ] All expected parameter groups visible (Project, Body, Rod & Groove, Strings, Channel, Tolerances)
- [ ] All expected user-editable parameters represented (16 fields: `project_name` + 15 geometry fields)
- [ ] Defaults populated (matches `docs/contracts/ZEROROD-PARAMETERS-V1.md`'s documented default values)
- [ ] Units understandable (mm shown next to geometry fields, in shown next to string gauges)
- [ ] Numeric field can be edited (type a new value, it visibly updates)
- [ ] `project_name` can be edited
- [ ] String gauges can be edited (including Add gauge / Remove gauge)
- [ ] Modified state appears (dirty badge shows after any edit)
- [ ] Reset restores defaults (values and dirty badge both return to loaded state)
- [ ] Invalid numeric input shows local feedback (e.g. non-numeric text, or a documented `> 0` field set to 0/negative)
- [ ] Correcting invalid input clears feedback
- [ ] Existing ZeroRod preview remains usable ("Load / Refresh ZeroRod" still renders the 3D model)
- [ ] Editing a field does NOT automatically regenerate the preview
- [ ] UI remains responsive while editing (no visible lag, no dropped keystrokes)
- [ ] App quits cleanly (no hang, no orphaned `zerorod-engine` process)

## Result

| Field | Value |
|---|---|
| Tester | *(pending)* |
| Date | *(pending)* |
| macOS | *(pending)* |
| Hardware | *(pending)* |
| Result | **PENDING** |
| Notes | Not yet performed — no interactive display available in the environment this milestone was engineered in. |

## Gate BUILD-023-M2 (human component)

**PENDING.** Engineering criteria are covered by `scripts/validate-build023-m2.sh`; this checklist's
completion is the remaining condition for the milestone's overall PASS, per the mandate's PARTIAL
allowance for "engineering works but a clearly noncritical UI interaction remains pending human
validation."
