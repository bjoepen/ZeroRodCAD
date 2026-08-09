# TE-002.2B — Human Validation Checklist

The optimized `.app` is built and available at:

```
experiments/te002-tauri/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app
```

(280.27 MiB, down from 673.34 MiB — see `Size-Comparison.md`.) It is unsigned; launching it the
first time requires the standard Gatekeeper override (right-click → Open, or
`xattr -d com.apple.quarantine` for automated use — same as TE-002.1).

All automated evidence in `Runtime-Validation.md`/`Results.md` confirms the shipped binary works
correctly at the process/protocol level. The items below require an actual human clicking through
the real window — not automatable in this environment (macOS Accessibility permissions), same
limitation TE-002.1's own `HUMAN-VALIDATION.md` documented.

## Checklist

- [x] App starts (double-click / `open`, no crash, window appears)
- [x] Model becomes visible after clicking "Load / Refresh ZeroRod"
- [x] Body geometry renders correctly
- [x] Rod geometry renders correctly
- [x] Virtual strings render correctly
- [x] Rotate (mouse drag) works
- [x] Zoom (scroll) works
- [ ] Window resize keeps the preview usable — not exercised in this pass; not reported by the tester either way, so left unchecked rather than assumed
- [ ] Reload (re-click Load/Refresh) works without needing to restart the app — not exercised in this pass; not reported by the tester either way, so left unchecked rather than assumed
- [ ] STL export produces a valid, openable file — **not applicable**: the PoC frontend (`experiments/te002-tauri/frontend/src/`) has no export UI at all, only `sidecar.js`'s preview request functions; there is nothing to click
- [ ] STEP export produces a valid, openable file — **not applicable**, same reason
- [ ] App shutdown (Cmd+Q / close window) exits cleanly — not exercised in this pass; not reported by the tester either way, so left unchecked rather than assumed
- [ ] No leftover `zerorod-engine` process after shutdown (check Activity Monitor / `ps aux`) — not exercised in this pass; not reported by the tester either way, so left unchecked rather than assumed

Additional, PoC-scope-relevant item (not in the original checklist above, added because it is the
one explicit limitation the tester called out):

- [ ] Parameter editing (changing `ZeroRodParameters` values through the UI and seeing the preview
  regenerate) — **NOT IMPLEMENTED / NOT TESTABLE**. The PoC UI has no parameter-editing surface yet
  (`preview`/`persistent_preview` only ever request the default model — see
  `docs/research/TE-002-Tauri-ThreeJS/Sidecar-Contract.md`). This is a scope gap, not a failure: it
  was never built, so it cannot fail a test. Explicitly **not** marked FAIL.

The unchecked items above are left unchecked deliberately — the tester's report did not cover them
one by one, and no unreported test is recorded here as passed. They do not change the overall
result below, which is scoped to what was actually exercised: the app launching, the ZeroRod model
rendering (body, rod, strings), and preview interaction (rotate, zoom).

## Result

| Field | Value |
|---|---|
| Tester | Project Owner / Human Validation |
| Datum | 2026-08-09 |
| macOS Version | not separately recorded by the tester |
| Hardware | not separately recorded by the tester |
| Ergebnis (PASS / FAIL / PARTIAL) | **PASS within implemented PoC scope** |
| Bemerkungen | App starts for real. The ZeroRod model is displayed, and the existing model parts (body, rod, virtual strings) render correctly. The model can be moved/rotated; zoom works; the existing preview interaction works. The app works within the scope of what the PoC actually implements, and the existing functionality was validated for real by a human, not simulated. Important limitation: parameter changes are **not yet implemented** in the PoC UI — this is explicitly a scope gap (NOT IMPLEMENTED / NOT TESTABLE), not a failure, and must not be read as one. |

## Gate E-B (TE-002.2B) verdict

**PASS within implemented PoC scope.** The optimized (293,892,882-byte / ~280.27 MiB) `.app` was
launched and interactively driven by a human on real macOS hardware, not just exercised through
automated process/protocol tests. Combined with Gate F-B (`Conclusion.md`, PASS — packaging/
regression evidence), TE-002.2B's evidence base is complete for what it was scoped to prove: the
optimized bundle preserves full PoC-scope functionality with no VTK, no PySide6/Qt, and no
performance or memory regression (`Results.md`). Parameter editing remains explicitly outside the
PoC's implemented scope and is therefore outside this validation's ability to test it — carried
forward as a Build 023 concern (`docs/migration/README.md`), not as an open defect here.
