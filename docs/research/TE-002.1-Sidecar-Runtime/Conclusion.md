# TE-002.1 — Conclusion

## Recommendation: Variant D — persistent + onedir

Not the variant assumed at the outset — the mandate's governing rule was measure before choosing,
and that's what decided it. The deciding evidence, in order of weight:

1. **Cold start**: onedir's 0.644 s vs. onefile's 17.305 s (persistent) / 15.789 s median
   (one-shot) — a ~24–27× difference, entirely attributable to PyInstaller self-extraction, not
   to anything architectural.
2. **Process termination reliability**: onefile has a structural orphaned-process risk on any
   Rust-triggered forced kill (timeout, crash-recovery restart, app-exit cleanup), because
   `tauri-plugin-shell`'s `CommandChild::kill()` only signals the top-level PID and onefile's real
   work happens in a separate forked child that isn't part of any process group. onedir has none
   of this risk, by construction — verified with direct kill tests, not inferred
   (`Process-Lifecycle.md`).
3. Warm-request latency (~0.13 s) and RSS growth (well under 1 MB over 20 requests) are
   essentially identical between C and D — packaging mode stops mattering once a process is
   already running, so neither of those numbers argues for onefile.

Points 1 and 2 together make this a clear result, not a close call: onedir wins on the one metric
that matters most for interactive UX (cold-start latency) and on the one metric that matters most
for reliability (clean process termination under every failure mode this evaluation tested), while
losing only on disk footprint (525 MiB vs. 135 MiB) and file count (368 vs. 1) — a real but
secondary cost for a desktop application, not weighed as decisive here.

## Gate E-A: PASS

Confidence: **MEDIUM**. Every engineering question this evaluation set out to answer was answered
with real, measured, cross-checked evidence: four real variants built and benchmarked (not
estimated), a genuine methodology bug found and fixed mid-benchmark (RSS on onefile builds) rather
than hidden, a decisive process-lifecycle finding obtained through direct kill tests rather than
assumed from documentation, a real `.app` bundle built and its *exact* bundled sidecar binary
(hash-verified, not a stand-in copy) driven successfully through the full persistent protocol,
zero VTK/PySide6 evidence at every layer checked, and no regression in the existing 241-test suite.

Not HIGH, for the same reason TE-002's own Gate D wasn't rated HIGH: an actual interactive
click-through-the-WebView confirmation was not possible in this sandboxed session (blocked by
macOS Accessibility permissions, same failure mode TE-002 already hit). This evaluation closed
that gap further than TE-002 did — by exercising the literal bundled binary through the real
protocol instead of only a standalone copy — but it did not, and could not, close it completely.
That is exactly what `HUMAN-VALIDATION.md` exists for.

## Per the mandate's explicit limit on what Claude may conclude at this stage

**PRODUCTIVE MIGRATION: READY FOR HUMAN VALIDATION.**

Not GO, and not PASS in any production sense — Gate E is split, and only Gate E-A (engineering) is
decided here. Gate E-B (human validation) is explicitly pending; the overall Gate E verdict
requires both.

## Architecture boundary and contract — confirmed unchanged

TE-002's core decisions all still hold, unmodified by TE-002.1: the WebView never spawns a
process directly (only Rust does, via app-registered commands); the `zerorod-sidecar/v1` and
`zerorod-mesh/v1` schemas are unchanged (only the persistent transport's request/response *count*
per process differs, not their shape); no gRPC/HTTP/WebSocket/MessagePack/protobuf/Redis/ZeroMQ
was introduced; `PreviewMesh`/`PreviewScene` remain untouched and renderer-agnostic.

## Remaining risks (carried forward or newly found)

- Interactive WebView confirmation still not closed in an automated session — needs
  `HUMAN-VALIDATION.md` to complete.
- CadQuery's VTK decoupling remains a locally-applied patch, not upstream (unchanged since
  TE-001.1).
- No idle-timeout cleanup for the persistent engine — it stays alive until an explicit shutdown,
  app exit, or a request failure triggers restart; a real product would likely want one.
- The `preview` command still only supports default parameters — the full `ZeroRodParameters`
  surface was never exposed through the sidecar contract, same scope limit as TE-002.
- Memory growth across 20 requests (~1 MB) is small and not alarming, but the sample size is too
  small to rule out slow drift over a much longer real session — not evaluated here.
- Full desktop-app feature parity (settings, project management, export dialogs) remains
  completely out of scope, same as every prior TE in this series.

## Explicitly not done (per the mandate's "NICHT TUN" list, unchanged)

PySide6 was not removed. No full Tauri migration was started. Build 022 was not started. The
existing UI was not redesigned. The parameter editor/export dialogs/settings were not migrated. No
auto-updater was added. No signing/notarization subproject was started. No binary mesh protocol
was developed. No new CAD core was introduced. No new repository was created. This ADR
(`ADR-DRAFT-TE0021.md`) is a draft, not finalized. No manual/human validation step was faked or
simulated — see `HUMAN-VALIDATION.md`.
