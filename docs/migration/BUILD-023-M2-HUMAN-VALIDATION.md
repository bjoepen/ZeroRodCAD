# Build 023 / Milestone 2 — Human Validation Checklist

Engineering completion for M2 (parameter panel, defaults loading, local draft/dirty/reset state,
local validation feedback, no automatic preview regeneration) is covered by automated evidence: see
`docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md` and `scripts/validate-build023-m2.sh`. This
document is the interactive click-through a human tester still needs to do — real WebView keyboard
input, focus behavior, and visual layout cannot be fully proven by jsdom-based unit tests alone.

This environment had no display/GUI access when the checklist below was drafted, so every item was
initially left **unchecked** rather than assumed, per the mandate's own allowance for this ("Claude
leaves unchecked if human clicking unavailable").

**Update:** the Project Owner has since performed this validation against the fresh release bundle
built for M2 (`docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md`'s artifact, commit `d691d95`) and
reported an overall **PASS**. That report did not itemize individual checklist rows, so the
itemized checkboxes below are left unchecked rather than retroactively marked — the "Result" table's
aggregate PASS is the authoritative record of what the Project Owner actually reported. No
additional or repeat validation was performed by Claude to produce this update.

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
| Tester | Project Owner |
| Date | not separately itemized by the tester's report |
| macOS | not separately itemized by the tester's report |
| Hardware | not separately itemized by the tester's report |
| Result | **PASS** |
| Notes | Reported directly by the Project Owner as an overall PASS against the M2 release artifact (commit `d691d95`). Individual checklist rows above were not itemized in that report and are left unchecked rather than retroactively assumed — the aggregate PASS in this table is the actual recorded result. |

## Gate BUILD-023-M2 (human component)

**PASS**, as reported by the Project Owner. Combined with the engineering gate
(`scripts/validate-build023-m2.sh`, PASS), **Gate BUILD-023-M2: PASS** overall — Milestone 2 is
COMPLETE.
