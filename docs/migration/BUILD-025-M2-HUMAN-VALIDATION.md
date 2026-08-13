# Build 025 / Milestone 2 — Human Validation Checklist

Engineering completion for M2 (automatic initial preview, no manual engine-start requirement,
technical controls relocated to Diagnostics, startup failure/retry UX) is covered by automated
evidence: see `docs/migration/BUILD-025-M2-PRODUCT-LIFECYCLE.md` and
`scripts/validate-build025-m2.sh`, including a real bundled-onedir-binary smoke test of the
`parameters_defaults` → `preview` sequence the automatic initial preview is built from. This
document is the interactive click-through a human tester still needs to do — first impressions,
timing/flicker judgment, and general "does this feel like a normal desktop app now" assessment are
not something a unit test (running under jsdom, no real WebView, no real GPU) can substitute for.

**Status: PENDING.** No human validation has been performed yet. Nothing below is marked `[x]`.

## Build under test

A fresh, uniquely-named release bundle must be built from this milestone's HEAD via:

```
./scripts/build-productive-desktop-app.sh release
```

then copied to a uniquely-named artifact, e.g.:

```
cp -R "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app" \
      "desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD-Build025-M2.app"
```

Exact absolute path, bundle size, and artifact-identity markers are recorded in the final
Abschlussbericht for this milestone, not here (this file is the checklist, not the build record).

Open command:

```
open "<absolute path to ZeroRodCAD-Build025-M2.app>"
```

(Unsigned — first launch needs the standard Gatekeeper override, right-click → Open.)

## Checklist

### Startup

- [ ] App starts without any manual engine action
- [ ] No "Start Engine" step is needed anywhere in the normal flow
- [ ] The default/current ZeroRod model appears automatically, with no click required
- [ ] No permanently empty viewport — either a model appears, or (on a simulated failure) a clear
      error/retry state does, never a silent blank pane

### Normal product UI

- [ ] The old technical Engine/Ping/raw-JSON controls are gone from the normal product surface
- [ ] The parameter panel remains understandable (no leftover technical jargon)
- [ ] Project controls (New/Open/Save/Save As) remain usable, in the same place as M1
- [ ] Export remains usable, in the same place as M1

### Diagnostics

- [ ] A "Diagnostics" control is reachable (not hidden, not requiring a native menu)
- [ ] Technical information (build/version, engine status, Python/CadQuery/OCP versions, protocol
      identifiers) is sensibly presented there
- [ ] Diagnostics does not feel like a required part of normal operation — the app works fully
      without ever opening it
- [ ] Opening/closing/refreshing Diagnostics does not restart the engine, regenerate the preview,
      mark the project dirty, or change export state
- [ ] "Refresh Status" works; there is no "Kill Sidecar" or other process-control action

### Preview

- [ ] Changing a parameter still updates the live preview
- [ ] Rotate works
- [ ] Zoom works
- [ ] Pan works
- [ ] Camera framing behaves as before (refits on first load / extreme changes, not on every edit)

### Project

- [ ] New
- [ ] Open
- [ ] Save
- [ ] Save As
- [ ] Dirty guard (Save/Discard/Cancel) still appears for unsaved changes
- [ ] Red macOS close button: clean project closes immediately; dirty project shows the guard;
      Cancel/Discard/Save all still behave correctly (M1 corrective-fix regression)

### Export

- [ ] "Export Model…" still works
- [ ] STL export
- [ ] STEP export
- [ ] Report export

### Error / Recovery

If a safe way to simulate this is available (e.g. temporarily renaming the bundled sidecar
resource before first launch, then restoring it and using Retry):

- [ ] A startup/engine failure shows an understandable message, not a raw error code or traceback
- [ ] Retry works and successfully recovers once the underlying problem is gone
- [ ] Technical details are available (Show Details) without cluttering the normal error message

### Shutdown

- [ ] Red close button still works (see Project section above)
- [ ] No `zerorod-engine` process remains running after the app quits (check with
      `pgrep -fl zerorod-engine`)

### Known Limitation

- [ ] The default macOS Quit / ⌘Q menu item still bypasses the unsaved-changes guard — this is a
      **known, pre-existing, documented limitation** (see
      `docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md`), unchanged by M2, and explicitly
      reserved for **Build 025 M4** to fix. It is not a new M2 regression — confirm it behaves the
      same as it did in the M1 build (quits immediately, no prompt, regardless of unsaved changes),
      then move on; do not attempt to fix it during this validation pass.

## Result

| Field | Value |
|---|---|
| Tester | *(Project Owner — not yet performed)* |
| Date | *(pending)* |
| macOS | *(pending)* |
| Hardware | *(pending)* |
| Result | **PENDING** |
| Notes | — |

## Gate BUILD-025-M2 (human component)

**PENDING.** Engineering gate (`scripts/validate-build025-m2.sh`) result is recorded separately in
the milestone's final Abschlussbericht. Engineering PASS does not by itself constitute
`BUILD-025-M2 CONSISTENCY GATE: PASS` for product purposes until this human validation is also
complete — Build 025 M3 is not authorized to start before then.
