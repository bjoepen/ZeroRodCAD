# TE-002.1 — Human Validation Checklist

**This file is a checklist for a human tester to fill in. Claude does not, and must not, mark any
field below as PASS itself.** Everything in this document up to this point (Discovery, Runtime
Variants, Benchmark Method, Performance, Memory, Process-Lifecycle, Packaging, Security, Results,
Conclusion) was produced through automated tooling and direct measurement, verified from real
build/test artifacts. What follows is the one category of check that genuinely requires a human
sitting in front of the actual running app — no manual check is claimed here that did not happen.

Gate E is split in two: **Gate E-A** (engineering — decided in `Conclusion.md`, PASS) and
**Gate E-B** (this document — decided by the human tester, currently **PENDING**). The overall
Gate E verdict requires both.

## How to start the test app

Absolute path to the built app:

```
/Users/bernd/Projekte/ZeroRodCAD-App/experiments/te002-tauri/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app
```

Start command:

```
open "/Users/bernd/Projekte/ZeroRodCAD-App/experiments/te002-tauri/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app"
```

**The app is unsigned** (no code signing/notarization was in scope for this evaluation — see
`Security.md`). macOS Gatekeeper will likely refuse to open it via a normal double-click on the
first launch, showing something like *"...cannot be opened because the developer cannot be
verified."* To open it anyway, for this one app, without disabling Gatekeeper system-wide:

1. In Finder, right-click (or Control-click) the `.app` → **Open** → confirm **Open** in the
   dialog that appears. This creates a one-time exception for this specific app only.
2. If that dialog doesn't appear, open **System Settings → Privacy & Security**, scroll to the
   Security section, and click **Open Anyway** next to the message about this app.

Do not disable Gatekeeper or SIP system-wide, and do not permanently re-sign or notarize this
build to work around this — the app is a technology-evaluation artifact, not a distributable
build.

## What to check

| # | Check | Result (PASS / FAIL / N/A) | Notes |
|---|---|---|---|
| 1 | App window opens, shows the toolbar (a "Load / Refresh ZeroRod" button, a status indicator, and a "Sidecar runtime: persistent + onedir (TE-002.1)" label) and an empty viewport | | |
| 2 | Clicking "Load / Refresh ZeroRod" changes the status indicator and, after a short pause, a 3D model appears in the viewport | | |
| 3 | The rendered model visually looks like a ZeroRod fishing-rod assembly (a body/handle shape plus a thinner rod shape) — not garbled geometry, not blank, not a crash | | |
| 4 | Clicking "Load / Refresh ZeroRod" again re-loads without needing to restart the app (confirms the persistent sidecar is actually being reused, not respawned) | | |
| 5 | Dragging in the viewport rotates the camera around the model (OrbitControls) | | |
| 6 | Scrolling / pinch in the viewport zooms in and out | | |
| 7 | Resizing the app window resizes the 3D viewport correctly (no stretching, no stale canvas size) | | |
| 8 | No visible error message, no crash, no frozen/unresponsive window during any of the above | | |
| 9 | Quitting the app (Cmd+Q or the red close button) closes the window promptly, without a hang | | |
| 10 | After quitting, no `zerorod-engine` process remains running (Activity Monitor, or `ps aux \| grep zerorod-engine` in Terminal, should show nothing) | | |

## Result

| Field | Value |
|---|---|
| Tester | |
| Datum | |
| macOS Version | |
| Hardware | |
| Ergebnis (PASS / FAIL / PARTIAL) | |
| Bemerkungen | |

## Gate E-B verdict

**PENDING** — to be filled in by the human tester above, not by Claude. Once filled in, combine
with Gate E-A (`Conclusion.md`, PASS) to determine the overall Gate E verdict for TE-002.1.
