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

- [ ] App starts (double-click / `open`, no crash, window appears)
- [ ] Model becomes visible after clicking "Load / Refresh ZeroRod"
- [ ] Body geometry renders correctly
- [ ] Rod geometry renders correctly
- [ ] Virtual strings render correctly
- [ ] Rotate (mouse drag) works
- [ ] Zoom (scroll) works
- [ ] Window resize keeps the preview usable
- [ ] Reload (re-click Load/Refresh) works without needing to restart the app
- [ ] STL export produces a valid, openable file
- [ ] STEP export produces a valid, openable file
- [ ] App shutdown (Cmd+Q / close window) exits cleanly
- [ ] No leftover `zerorod-engine` process after shutdown (check Activity Monitor / `ps aux`)

Left intentionally unchecked — human tester to complete.
