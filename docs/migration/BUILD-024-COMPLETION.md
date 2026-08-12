# Build 024 — STL / STEP Export Workflow — Completion Record

## Status

**COMPLETE.** All four milestones (M1–M4) are engineering-complete with Gate PASS; both
Human-Validation-bearing milestones (M2, M3) are Human-Validation PASS. Master gate:
`scripts/validate-build024.sh` → `BUILD-024 CONSISTENCY GATE: PASS`.

## Purpose

Build 022 proved the Tauri v2 + Rust + persistent Python sidecar + Three.js desktop architecture.
Build 023 made the model interactive (parameter editing, live preview). Build 024 makes the model
useful *outside* the application: the user can export the model they are actually looking at to
real STL, STEP, and Markdown-report files on disk, through a native macOS directory dialog, with
overwrite handling and robust failure/recovery behavior. M4 (this record) is an integration and
completion milestone — it adds no export feature, no UI change, and no architecture change; it
consolidates, audits, and closes the build.

## Baseline

- Build 022: COMPLETE / PASS (`docs/migration/BUILD-022-COMPLETION.md`).
- Build 023: COMPLETE / PASS (`docs/migration/BUILD-023-COMPLETION.md`).
- Build 024 M1 (`f2a7ce9`): COMPLETE / Gate PASS.
- Build 024 M2 (`fb53566`, bugfix over `31d1d11`): COMPLETE / Gate PASS, Human Validation PASS
  (Round 2; Round 1 found a real defect, see "Human Validation Matrix" below).
- Build 024 M3 (`72768bd`): COMPLETE / Gate PASS, Human Validation PASS.
- Build 024 M4 (this milestone): branched from `72768bd`, working tree clean at branch time.

## Milestone Matrix

| Milestone | Engineering | Human Validation | Gate |
|---|---|---|---|
| M1 — Export Architecture & Contract Foundation | PASS | N/A (no UI yet) | COMPLETE — `BUILD-024-M1: PASS` |
| M2 — Native Save Dialog & Export Controls | PASS | PASS (Round 2, after a Round 1 fail + fix) | COMPLETE — `BUILD-024-M2: PASS` |
| M3 — Export Robustness & Edge Cases | PASS | PASS | COMPLETE — `BUILD-024-M3: PASS` |
| M4 — Integration & Completion | PASS (master gate) | N/A — no runtime/product change made | COMPLETE — `BUILD-024: PASS` |

Per the mandate's own instruction, M4 does not require a redundant human click-through: it changed
no runtime code, no UI, and no product behavior — only documentation, validation tooling, and a
clean reproducible build.

## Human Validation Matrix

| Milestone | Round | Result | Notes |
|---|---|---|---|
| M2 | 1 | **FAIL** | Real Tauri IPC argument-binding defect: `engine_export`/`engine_export_preflight` used a plain `#[tauri::command]`, so Tauri's default camelCase binding rejected the frontend's (contract-correct) snake_case `output_directory` payload key — `invalid args \`outputDirectory\` ... missing required key outputDirectory`. Root cause and fix: `docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md`. |
| M2 | 2 | **PASS** | Fixed with `#[tauri::command(rename_all = "snake_case")]` on both commands, plus a new real-IPC-dispatch regression test module (`ipc_argument_binding`) so a mocked-`invoke()` frontend test can never again hide this class of defect. Native directory selection, export, STL/STEP/report generation, and opening the exported model all confirmed working (`docs/migration/BUILD-024-M2-HUMAN-VALIDATION.md`). |
| M3 | 1 | **PASS** | Validated against a uniquely named artifact, `ZeroRodCAD-Build024-M3.app`, built from M3's exact HEAD (`72768bd`). Artifact identity independently re-verified during M4 (see "Artifact Identity" below): frontend asset `index-CV7-6lJU.js`, SHA-256 `9fd28961e24823f08a728a9db529475f301d1f2d3938ae378d8ed1fbd6b11bde` (exact match), and the compiled `invalid_export_result` marker, all confirmed present in the tested bundle. Full record: `docs/migration/BUILD-024-M3-HUMAN-VALIDATION.md`. |
| M4 | — | N/A | No product/runtime change made this milestone; nothing new for a human to validate. |

## Final Architecture

Unchanged from `ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md` (re-verified, 0 deviations):

```text
ZeroRodCAD Desktop 2.0
    Tauri v2 (native shell + WebView + Three.js preview)
    Rust process / IPC layer (owns the sidecar lifecycle end to end)
    Persistent Python 3.13 sidecar (PyInstaller onedir)
        ZeroRodCAD engine (unchanged) + CadQuery + cadquery-ocp-novtk
        STL / STEP / Markdown report export
```

- **Tauri**: v2, `@tauri-apps/cli`/`@tauri-apps/api` `^2.` pinned. Unchanged.
- **Three.js**: preview renderer, unchanged since Build 022 M3.
- **Rust process ownership**: `engine.rs` (lazy spawn, persistent reuse, 30 s timeout, crash
  detection + restart-once, graceful shutdown) is byte-for-byte unchanged since M1 (`f2a7ce9`) —
  export is "just another request" through the existing `engine::request` entry point, exactly as
  the Build 024 handoff anticipated. Not touched by M4.
- **Persistent sidecar**: unchanged pattern (`_run_export_command`/`_run_export_preflight_command`
  follow `_run_preview_command`'s exact shape).
- **Python / CadQuery / cadquery-ocp-novtk**: unchanged; `zerorodcad.export.export_project` remains
  canonical and was not rewritten — Build 024 exposed it, never reimplemented it.
- **OCP strategy**: `cadquery-ocp-novtk` (not `cadquery-ocp`) confirmed in the packaging build
  environment.
- **Packaging**: PyInstaller onedir, no onefile fallback, hash-gated dylib dedup.
- **IPC**: private `zerorod-sidecar/v1` JSON over stdin/stdout — no HTTP/WebSocket/gRPC.
- **WebView capability**: exactly `["core:default", "dialog:allow-open"]` — the one narrow,
  documented delta introduced in M1 and unchanged since. No `fs:*`, no `shell:*`/`process:*`, no
  `dialog:allow-save/message/ask/confirm`.
- **Native directory dialog**: `tauri-plugin-dialog`, `dialog:allow-open` only — the WebView
  receives an opaque path string back and hands it to the Rust-owned `engine_export` command; it
  never gets filesystem read/write/list capability of its own.

**Deviations found: 0.**

## Export Workflow

```text
accepted parameters (never the still-debouncing draft)
    -> visible Three.js model
    -> "Export Model..." trigger
    -> native directory dialog (tauri-plugin-dialog, dialog:allow-open)
    -> export preflight (sidecar export_preflight + Rust engine_export_preflight)
    -> overwrite confirmation, only if a conflict is reported
    -> Rust engine manager (engine::request, same persistent-sidecar path as preview)
    -> persistent Python sidecar
    -> zerorodcad.export.export_project (unmodified engine-level export)
    -> STL + STEP + Markdown report written to disk
    -> sidecar-side post-export verification (exists + non-empty, all 3 outputs)
    -> Rust-side structural result validation (export_result.rs, M3)
    -> success/error surfaced to the WebView, backend-supplied filenames only
```

## Accepted-State Semantics

Export always sources the frontend's `accepted` parameter state — the values currently represented
in the preview, never a still-debouncing `draft`. `export_panel.ts`'s state machine stays disabled
while live preview is pending/updating, so "Export" always means exactly the model on screen. Proven
again this milestone with a fresh real-subprocess sequence (`scripts/validate-build024.sh`): a
`body_width: 38 -> 60 mm` alternate export produces a report containing `60.00 mm` and STL bytes
that differ from the default export, while the default export's own report does not contain
`60.00 mm` — confirmed via the productive, freshly rebuilt sidecar binary, not a unit-level mock.

## Native Dialog

`tauri-plugin-dialog`'s open/folder picker, `dialog:allow-open` only — no save dialog, no
message/ask/confirm dialog capability. The WebView receives a single opaque path string; it never
gets a directory listing or file-content read capability. Human-Validation-confirmed working
(M2 Round 2, M3).

## Preflight

`export_preflight` (sidecar) + `engine_export_preflight` (Rust) report per-file conflicts using the
engine's own `zerorodcad.export.expected_output_filenames` helper — never a duplicated/reimplemented
TypeScript filename reconstruction. Verified this milestone: empty destination → no conflict;
existing output → conflict (`has_conflicts: true`); cancel → no export attempted; confirm → exactly
one subsequent export request.

## Overwrite

Silent overwrite-in-place after confirmation — the product's original, deliberate M1 decision,
unchanged through M2/M3/M4. The preflight/export TOCTOU race was investigated in M3 and found to
reduce, in the worst case, to this same accepted overwrite behavior — no backend recheck was added
(see `docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md`, "TOCTOU"). Re-confirmed unchanged in M4.

## Output Verification

Two independent, non-duplicating layers, neither of which can be bypassed:

1. **Sidecar-side (M1)**: `path.is_file() and path.stat().st_size > 0` for all three expected
   outputs, immediately after `export_project` returns — the backstop against CadQuery's documented
   silent-no-op-on-unwritable-directory behavior.
2. **Rust-side (M3)**: `export_result.rs` structurally validates the *shape* of whatever JSON the
   sidecar returns (`output_directory`, `files` role set, `path` presence, `has_conflicts`/
   `conflicts` consistency) before it can ever reach the WebView as success — guards against a
   future sidecar change accidentally omitting/renaming a field, which the sidecar-side check alone
   cannot catch.

## Robustness

Full inventory (failure modes A–T) is `docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md`'s own
table — carried forward unchanged; M4 added no new failure mode and found no gap in it. Summary:
missing/zero-byte output, invalid parameters, sidecar structured errors, malformed sidecar
responses, spaces/Unicode paths, repeated export, and preview/export interleaving are all TESTED
(real, non-mocked-below-the-boundary); sidecar crash/timeout injection and real OS disk-full remain
CODE-INSPECTED / NOT SAFELY TESTABLE respectively, honestly documented as such, not claimed as
empirically proven.

## Retry Policy

`engine.rs`'s existing generic retry-once-on-crash/timeout policy (unchanged since M1, byte-for-byte
frozen) is retained for `export`, backed by M3's evidence-based decision:

- Every export write is a complete, from-scratch overwrite — never append, never partial-update.
- STL and the Markdown report are byte-identical across repeated identical-parameter exports
  (directly tested).
- STEP is **not** byte-identical across repeats — a documented CadQuery/OCP internal
  entity-numbering/ordering nondeterminism, not a geometry defect (see "Known Limitations").
- A retry can therefore never leave a worse result than a single successful export would.

No command-specific retry-suppression logic exists or was added. Not reopened in M4 — no new
evidence emerged to revisit this decision.

## Error Model

Structured `{code, message, details?}` throughout — `EngineError`/`isEngineError`/`SidecarError`,
unchanged since Build 022/023. Export-specific codes (`export_incomplete`, `export_write_failed`,
`invalid_export_result`) are additive within this existing envelope. No raw Python traceback ever
crosses the sidecar boundary. A rejected/malformed result never renders as success in the frontend;
a stale error clears on the next successful attempt.

## Security

Re-verified this milestone, 0 deviations:

- WebView shell/process/broad-filesystem permission: **NO**.
- WebView capability: exactly `["core:default", "dialog:allow-open"]`.
- CSP: unchanged — `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost`.
- IPC: private stdin/stdout, no network surface.
- Rust owns the sidecar lifecycle end to end.
- Remote services / external CDN: **NONE**.

## Performance

No regression across Build 022 → 023 → 024 M1/M2/M3. Export: ~0.13 s warm (measured repeatedly
across M1–M3, ~200x margin under the unchanged 30 s timeout). `export_preflight`: ~0.036 s full
process round trip. M4 performed no new optimization work (not in scope) and found no evidence of
regression in this milestone's own full test/gate runs.

## Memory

M3's bounded 20-export sequence: +5.07% RSS (324.7 MB -> 341.2 MB), tapering — consistent with
CadQuery/OCP warm-up caching stabilizing, not an unbounded per-call leak. M4 performed no new
endurance testing (not in scope; M3's evidence stands, no new evidence to revisit it).

## Packaging

`scripts/build-productive-desktop-app.sh release`: PyInstaller onedir sidecar, Tauri release build,
hash-gated post-bundle dylib dedup, no onefile fallback. See the final report (below the fold in the
conversation's completion report) for this milestone's own clean-rebuild measurement and comparison
against the M3 baseline (299,743,617 bytes / ~285.86 MiB / 201 files / 57 dirs / 77 symlinks).

## Dependency Invariants

Meaningful detection (filename-glob search across the actual built bundle, excluding the
`cadquery_ocp_novtk` false-positive substring match) re-confirms, in the fresh M4 rebuild:

| Dependency | Count |
|---|---|
| VTK | 0 |
| PySide6 | 0 (productive bundle) |
| Qt | 0 |
| numba | 0 |
| llvmlite | 0 |
| scipy | 0 |

## Test Summary

As of Build 024 M4's own clean run (this milestone made no source change, so these figures are
identical to the M3 baseline):

- **Python**: 347 passed, 1 skipped (pre-existing, unrelated TE-001 Gate-A re-evaluation note).
  Ruff clean.
- **Rust**: 42/42 passed. `cargo fmt --check` / `cargo clippy --all-targets -- -D warnings` clean.
- **Frontend**: 207 passed, 1 skipped. TypeScript clean. Production build clean — identical output
  asset hash to M3 (`index-CV7-6lJU.js`), confirming no frontend drift.

## Artifact Identity

The Build 024 M3 mandate's own lesson — "a generic bundle path is not artifact identity" — is
carried forward as a durable practice (see "Process Improvements" in the final report). For this
milestone's own re-verification of the already-validated M3 artifact:

| Proof | Value |
|---|---|
| Frontend asset filename | `index-CV7-6lJU.js` |
| Frontend asset SHA-256 | `9fd28961e24823f08a728a9db529475f301d1f2d3938ae378d8ed1fbd6b11bde` |
| Compiled Build-024-specific marker | `invalid_export_result` (present in the compiled binary's string table) |

All three independently re-verified against the local `ZeroRodCAD-Build024-M3.app` during M4 and
found to match exactly. The final M4 artifact's own identity proof (frontend hash, compiled marker,
deterministic bundle fingerprint) is recorded in the completion report produced at the end of this
milestone, once the final clean build is complete.

## Known Limitations

Carried forward from M3, none newly introduced by M4:

1. Real sidecar-crash-during-export and real request-timeout-during-export remain CODE-INSPECTED,
   not empirically tested — no crash/timeout-injection harness exists for any command in this
   codebase. The retry-safety *conclusion* is evidence-based (write idempotency, directly tested);
   the crash-detection *mechanism* is pre-existing, unchanged `engine.rs` behavior.
2. Real OS-level disk-full remains NOT SAFELY TESTABLE; only the error-mapping boundary is verified
   (SIMULATED).
3. STEP export is not byte-identical across repeated identical-parameter exports — believed cosmetic
   (internal entity numbering/ordering, not geometry), not independently verified beyond the direct
   line-diff performed during M3's investigation. Not treated as a defect.
4. No STL/STEP format-level structural sanity check (header/footer markers) exists beyond the
   existing non-empty-file check — flagged as a possible narrow future addition, not implemented (no
   new CAD parser dependency).
5. Long destination-path testing was not separately exercised — no evidence of a length-related
   defect exists, but this was not empirically proven either.
6. Project persistence, full desktop feature parity, and signing/notarization are not yet
   implemented — intentionally deferred to Build 025/026, not defects.

## Explicit Non-Scope (this milestone)

Per the M4 mandate, none of the following were done, added, or reopened in M4: new export feature,
export UX redesign, STL-only/STEP-only export, project persistence, recent files, Finder
integration, parameter UI redesign, preview redesign, engine redesign, protocol v2, PySide6 removal,
legacy UI changes, signing/notarization, or starting Build 025.

## Build 025 Handoff

Full handoff: `docs/migration/BUILD-025-HANDOFF.md`. Build 025 inherits a working, tested, packaged
export workflow on top of the Build 022/023 foundation and picks up Desktop Feature Parity (remaining
application workflows, settings, project open/save, shortcuts, desktop integration, accessibility)
per the existing `ROADMAP.md` build-sequence table — no new scope invented here.
