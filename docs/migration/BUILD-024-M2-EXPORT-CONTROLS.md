# Build 024 M2 — Native Save Dialog & Export Controls

Status: **engineering COMPLETE / Gate BUILD-024-M2: PASS** — Human Validation **PENDING**.

## Objective

M1 (`docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md`) proved the export boundary — a
sidecar `export` command and a Rust `engine_export` command exposing the existing,
unmodified `zerorodcad.export.export_project` — but built no UI. M2's job is to make that
boundary usable: a real "Export Model…" trigger in the productive desktop app, a native
macOS directory dialog, deterministic interaction with live preview, and a deliberate,
user-safe answer to the silent-overwrite behavior M1 discovered rather than fixed.

## M1 baseline (unchanged, reused as-is)

- `zerorodcad.export.export_project(output_directory, parameters)` — still the canonical
  engine export call, still unmodified.
- Sidecar `export` command (`src/zerorod_sidecar/main.py`) and Rust `engine_export`
  (`desktop/src-tauri/src/commands.rs`) — unmodified.
- `select_export_directory` (Rust) — the native folder-picker command, `dialog:allow-open`
  only, unmodified.
- Canonical export-source semantics: **`accepted`**, never the draft (`parameter_panel.ts`'s
  `getAcceptedRequest()`).
- `export_incomplete` — the post-export file-existence/non-empty verification the sidecar
  performs (CadQuery's STL/STEP exporters can silently no-op on an unwritable directory).
- Silent-overwrite-in-place — M1 explicitly left the *UX* answer to this to M2.

## What M2 adds

### 1. A minimal, additive engine-side helper (not a rewrite)

`src/zerorodcad/export.py` gained one small pure function,
`expected_output_filenames(project_name) -> dict[str, str]`, extracted from the filename
logic `export_project` already had inline (`_safe_name` + three fixed suffixes).
`export_project` itself now calls this helper instead of duplicating the filename
computation — same behavior, single source of truth, so a preflight check can never drift
from what `export_project` actually produces. `_safe_name`, `build_body`, `build_assembly`,
`validate_parameters`, and every other engine internal are untouched.

### 2. Overwrite preflight — sidecar `export_preflight` command

A new, side-effect-free sidecar command (`src/zerorod_sidecar/main.py`'s
`_run_export_preflight_command`) that takes the exact same request shape as `export`
(`{"parameters": {...}, "output_directory": "..."}`) and returns which of the expected
output filenames already exist in that directory — **without performing an export and
without listing the directory's actual contents**. It only checks the fixed, known set of
filenames `expected_output_filenames` computes:

```jsonc
{
  "output_directory": "/Users/example/exports",
  "expected_files": [
    {"role": "body_stl", "filename": "cbg-open-g-body.stl"},
    {"role": "assembly_step", "filename": "cbg-open-g-assembly.step"},
    {"role": "report_markdown", "filename": "cbg-open-g-report.md"}
  ],
  "conflicts": [{"role": "body_stl", "filename": "cbg-open-g-body.stl"}],
  "has_conflicts": true
}
```

Rust: `engine_export_preflight` (`commands.rs`) forwards `parameters`/`output_directory`
verbatim through `engine::request(..., "export_preflight", ...)`, exactly mirroring
`engine_export`'s own shape — Rust does not interpret either value. No new capability is
needed (no dialog, no filesystem access — the check happens sidecar-side, which already had
disk access for `export` itself).

Frontend: `export.ts` gained `ExportPreflightResult`/`ExportPreflightFile` types and
`requestExportPreflight(values, outputDirectory)`, mirroring `requestExport`'s own shape and
tests.

### 3. The Export UI — `export_panel.ts`

A new, isolated module (§36 of the mandate: not mixed into parameter state, the renderer,
or the live-preview scheduler) that owns the entire export flow as an explicit state
machine:

```text
idle → selecting_destination → checking_destination →┬→ exporting → success
                                                       └→ confirm_overwrite → exporting → success
                                                                            └→ idle (cancel)
any state → error (on any structured failure)
```

It talks to the rest of the app only through a small `ExportPanelIO` interface
(`getAcceptedRequest`, `getLivePreviewStatus`) — the same shape of indirection
`PreviewIO` already uses to connect `parameter_panel.ts` to `preview.ts` without either
module importing the other's internals.

**Label**: **"Export Model…"** — chosen over "Export STL" (the action also produces STEP +
a report, so a format-specific name would be misleading) and over "Save" (project
persistence is Build 025 scope, not this). "Export Model…" matches the existing
"Load / Refresh ZeroRod" button's plain-language style and its trailing ellipsis signals
(as on macOS generally) that it opens a further dialog.

**Placement**: directly below the parameter panel, in a new `.export-panel-container`
section inside a `.parameters-column` wrapper `main.ts` introduces (previously `.parameters`
was a single fixed-width sidebar column; it is now the top child of a flex column, with the
export panel as its sibling) — visually "near Apply," as the M1 handoff suggested, without
being DOM-nested inside `parameter_panel.ts`'s own wholesale-`innerHTML`-rebuilt container
(which would make the two modules' rendering fight each other).

**Trigger enablement** — computed from `ExportPanelIO`, re-evaluated on every relevant
change:

```text
enabled  ⟺  the panel is in idle/success/error (not mid-flow)
         AND io.getAcceptedRequest() is not null
         AND io.getLivePreviewStatus() is "up-to-date" OR "error"
```

"error" is included deliberately: a failed live-preview attempt does not discard
`accepted` — the model currently visible in the viewport is still the last successfully
accepted one, so export remains meaningful. "pending"/"updating" disable the trigger (§30 of
the mandate: "Strong preference: disable export until live-preview settles") — even though
export sourcing `accepted` already structurally prevents exporting an invisible/unaccepted
draft (a hard invariant, not a preference; see M1's "Consistency of what is exported"), this
is purely about "Export" always visibly meaning "the model I am currently looking at."

**`accepted`/live-preview change notification**: `parameter_panel.ts` gained one new,
optional third constructor argument, `onChange?: () => void`, called from inside
`setLiveStatus` (the single place `livePreviewStatus`, and everything that changes in
lockstep with it — including `accepted` — actually mutates). This is what lets an
Apply-triggered request (which sets "updating" synchronously via
`live_preview.ts`'s `onRequestStart`, not through `updateStatusUI`) also disable the export
trigger immediately, not just automatic debounced edits. `main.ts` wires this to the export
panel's `refreshEnablement()` via a small forward reference (`exportPanelRef`, assigned
synchronously right after both controllers are constructed) — no shared mutable state, no
new state-management library (§37 of the mandate).

**Dialog cancellation**: `selectExportDirectory()` returning `null` (M1's own,
already-`None`-on-cancel design) short-circuits back to `idle` with a subtle transient note
("Export cancelled") — no error state, no `EngineError`, no export request ever dispatched.

**Overwrite confirmation**: an in-panel state (`confirm_overwrite`), not a native OS dialog —
M1 deliberately did **not** grant `dialog:allow-ask`/`dialog:allow-confirm` (see "Security"
below), so a native `ask`/`confirm` popup was never an option; this stays consistent with
that boundary. Lists the conflicting filenames (from the preflight result, not
frontend-reconstructed), offers **Cancel** / **Replace**. Cancel → back to `idle`, no export
request, no files touched (§27). Replace → calls `requestExport` directly with the
already-selected directory, **without** a second preflight round trip (the first result is
still valid — nothing else could have changed the directory in between from inside this
app).

**"Exporting…" indicator**: delayed by 150 ms (mirrors `parameter_panel.ts`'s own
`UPDATING_DISPLAY_DELAY_MS` pattern) — real export is ~0.13 s warm, so the text should
essentially never be visible in the common case; only a slow cold-start export or an
unusually slow disk actually shows it. No fake percentage progress.

**Success**: shows the destination directory and the generated filenames — **taken
verbatim from the backend's `ExportResult.files`**, never reconstructed in TypeScript (§18
of the mandate — avoids drift from the engine's own `_safe_name` sanitization, the same
discipline the preflight helper applies).

**Error**: `formatExportError` maps known `EngineError` codes to a concise, human sentence
(never a raw code, never a traceback — the sidecar already guarantees no traceback crosses
the boundary):

| Code | Message shown |
|---|---|
| `invalid_destination` / `export_invalid_destination` | "The selected destination is not valid. Choose a different folder." |
| `export_permission_denied` | "Permission denied writing to the selected destination." |
| `export_write_failed` | "The selected destination could not be written to." |
| `export_incomplete` | "Export did not complete — missing: `<roles>`. Nothing was fully exported; try again." |
| `invalid_parameters_domain` / `invalid_parameter_type` / `invalid_parameters` / `invalid_parameters_schema` | "The current model parameters are invalid; fix them before exporting." |
| anything else | `"Export failed: <message>"` |

`export_incomplete` is never rendered as `success` — it throws (same as every other
sidecar error), so it always lands in the `error` state.

## Overwrite decision (§23–§29 of the mandate)

**Decision: ask before overwriting, using a backend-driven preflight check, not a broad
filesystem grant to the WebView.** The check happens sidecar-side (already has disk access
for `export` itself); the WebView only ever receives the same two things it already can —
role/filename pairs, never a directory listing. Naming/collision behavior (§29:
`"A!B"`/`"A?B"` both sanitizing to `"a-b"`) is **not** re-solved here — it is inherited
unchanged from `export_project`'s existing sanitization, and preflight naturally detects the
resulting collision as an ordinary conflict, exactly as the mandate expects ("Document this
as current behavior. Do not add uniqueness suffixes in M2").

## Live-preview interaction (§12/§30 of the mandate)

No new concurrency model. Export still flows through the same `Mutex`-guarded
`engine::request` entry point as `preview` (unchanged since M1) — an `engine_export` or
`engine_export_preflight` call issued while a preview request is in flight simply queues
behind it, exactly as before. The *new* piece is UI-only: the trigger is disabled while
`livePreviewStatus` is `"pending"` or `"updating"`, via the `onChange` notification
described above, so a click can never even be attempted mid-flight — not because it would
be unsafe (it wouldn't; `accepted` cannot reflect an in-flight request's not-yet-committed
value), but so "Export" always visibly corresponds to what's on screen.

## `project_name` behavior (§34 of the mandate)

Unchanged from Build 023 M4: a `project_name`-only edit is a "metadata-only" change that
`accepted` picks up **immediately** (no engine round trip, no live-preview request — see
`parameter_panel.ts`'s `isGeometryUnchanged` gate) — so exporting right after changing only
`project_name` (with no pending geometry edit) exports under the new name immediately, with
no live-preview wait. Verified directly: `test_export_project_name_shapes_generated_filenames`
(sidecar unit test, unchanged from M1) and the new
`test_export_preflight_filenames_match_actual_export_output` prove preflight and export agree
on the sanitized filename set for an arbitrary `project_name`.

## Security boundary (§8/§20/§24/§40/§41 of the mandate)

**No capability delta from M1.** `desktop/src-tauri/capabilities/main-capability.json` is
unchanged: `["core:default", "dialog:allow-open"]`. `engine_export_preflight` needs no new
permission — it is a plain Tauri command forwarding to the already-registered sidecar
process, exactly like `engine_export`. No `dialog:allow-save`, no `dialog:allow-ask`/
`dialog:allow-confirm` (the overwrite confirmation is in-panel UI, not a native dialog — see
above), no `fs:*`, no `shell:*`, no `process:*`. CSP (`tauri.conf.json`) unchanged, verified
byte-for-byte against the exact string M1's own gate checks.

## Export state machine (§15/§16 of the mandate)

```text
idle → selecting_destination → checking_destination → exporting → success
                                                   ↘ confirm_overwrite → exporting → success
any non-terminal state → error (on any structured failure)
error/success → idle-equivalent trigger re-enablement (getAcceptedRequest()/status permitting)
```

`exporting` disables the trigger and blocks a duplicate dispatch (verified directly —
`export_panel.test.ts`'s "does not dispatch a second export while one is in flight" clicks
the trigger twice and asserts `requestExport` was called exactly once).

## Tests

- **Frontend**: `export.test.ts` (+3 for `requestExportPreflight`), `export_panel.test.ts`
  (new, 19 tests covering rendering/enablement, dialog invocation/cancellation, preflight →
  export, duplicate-click blocking, success/error/`export_incomplete` presentation, and the
  full overwrite conflict/cancel/confirm flow), `parameter_panel.test.ts` (+2 for the new
  `onChange` hook, including the synchronous "updating" notification an Apply click
  triggers). Full suite: **203 passed, 1 skipped** (up from Build 023's 180 baseline).
- **Rust**: `protocol.rs` gained 2 wire-shape tests for `export_preflight`'s request/response
  shape (mirroring the existing `export` ones) — no new command-level unit tests beyond
  that, matching M1's own precedent (`engine_export`/`select_export_directory` need a live
  `AppHandle`/`State`, so their correctness is proven at the protocol-wire-shape level plus
  the real end-to-end evidence below). Full suite: **28/28 passed**. `cargo fmt --check` and
  `cargo clippy --all-targets -- -D warnings` both clean.
- **Python**: `test_export.py` (+2 for `expected_output_filenames`), `test_zerorod_sidecar_main.py`
  (+9 for `export_preflight`: no-conflict, does-not-export, one-conflict, multiple-conflict,
  sanitized-name-collision, filenames-match-actual-export, missing/empty destination,
  JSON-serializable/no-traceback), `test_zerorod_sidecar_persistent.py` (+1 real-subprocess
  sequence: preview → preflight (no conflict) → export → preflight (conflict, 3 files) →
  export (overwrite) → preview → shutdown, against the real TE-001.1-patched interpreter).
  Full repository suite: **338 passed, 1 skipped** (the skip is the pre-existing, unrelated
  TE-001 Gate-A re-evaluation note). Ruff clean.

## Real export evidence (§45 of the mandate)

`TestRealPersistentSubprocess::test_real_subprocess_preflight_overwrite_confirm_sequence`
drives a single real subprocess (against `.venv-novtk-poc`, the same VTK-free,
TE-001.1-patched interpreter class used as "real, not mocked" evidence throughout this
migration) through the full M2 sequence in one persistent process:

1. `preview` (defaults) — `ok: true`.
2. `export_preflight` on an empty directory — `has_conflicts: false`.
3. `export` (defaults) — 3 real, non-empty files written.
4. `export_preflight` on the *same* directory again — `has_conflicts: true`, all 3 files
   listed (proving preflight and `export` share exactly the same naming logic, not a
   separately duplicated one).
5. `export` again with `body_width: 60` (the "confirm overwrite" request) — succeeds;
   same three filenames (same `project_name`), and the final on-disk report shows
   `60.00 mm`, not the default `38.00 mm` — direct proof the overwrite actually replaced the
   content rather than being silently skipped. (Byte-level STL content inequality between
   two different-parameter exports is separately proven, without this test's
   read-only-after-both-writes limitation, by the pre-existing
   `test_export_overwrites_existing_output_files_in_place` in `test_zerorod_sidecar_main.py`,
   which issues two `handle_request` calls directly and can inspect disk state in between.)
6. `preview` again — still `ok: true` (sidecar healthy after two exports).
7. `shutdown` — clean exit, `returncode == 0`.

Additionally, the productive PyInstaller onedir sidecar was rebuilt from this M2 commit and
smoke-tested directly through its real binary: `preview` → `export` → `export_preflight` →
`shutdown`, all `ok: true`. (The PyInstaller build log again showed the
`Hidden import 'OCP.TKernel' not found` / `Hidden import 'cadquery.exporters' not found`
messages M1 first documented as non-fatal — confirmed non-fatal again here: the resulting
binary's real request/response round trip works correctly. These are PyInstaller
warnings that don't reflect missing functionality, not build failures — no action taken, no
`packaging/`/spec file touched.)

## Performance (§46/§47 of the mandate)

| Scenario | Measured |
|---|---|
| `export`, warm process (default parameters) | 0.150 s |
| `export`, warm process (alternate parameters, second call) | 0.129 s |
| `export_preflight`, full process round trip (cold interpreter start included) | 0.036 s |

Both remain far inside M1's own measured envelope (~0.13 s warm, ~1.45 s cold) and the
existing 30 s request timeout (`engine::REQUEST_TIMEOUT_SECS`, unchanged — no evidence
supports changing it). Dialog/user interaction time is explicitly **not benchmarked** (human
time, not engine time) — only the engine round trip is measured above.

## Packaging (§48/§49 of the mandate)

Fresh release build from this M2 commit, using the established productive pipeline
(`scripts/build-productive-desktop-app.sh release`) — PyInstaller onedir, Tauri release,
hash-gated dylib dedup, no onefile fallback:

```text
bytes:    299,736,337
MiB:      285.9
MB:       299.74
files:    201
dirs:     57
symlinks: 77
```

Compared to the Build 022/023 baseline (285.3 MiB / 299,160,577 bytes / 201 files / 77
symlinks): **+0.6 MiB**, fully explained by `tauri-plugin-dialog`'s additional linked Rust
crates (`rfd`, `objc2-app-kit`, `objc2-web-kit`, etc. — native macOS dialog bindings) already
present in the app binary since M1; M2 adds no new Cargo dependency and no new sidecar
dependency. VTK / productive PySide6 / Qt / numba / llvmlite / scipy: all **0** (unchanged
from every prior build's own verification — M2 touches none of the packaging spec).

**Human Validation artifact** (§50 — mandatory, not to be omitted):

```text
Absolute path: /Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app
Open command:  open "/Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
```

## Limitations

1. Independent STL-only/STEP-only export is still not implemented (unchanged limitation
   from M1 — `export_project` has no per-format entry point; a genuine, deferred engine-level
   product decision, out of scope for M2 too).
2. `export_write_failed` (the `OSError`/`ENOSPC` disk-full path) remains unverified — M1's
   own documented limitation, unchanged; not safely reproducible in this environment.
3. The overwrite confirmation is in-panel UI, not a native OS alert — a deliberate
   consequence of the security boundary (no `dialog:allow-ask`/`dialog:allow-confirm`
   granted), not an oversight.
4. No auto-open-destination-in-Finder convenience action (§19 of the mandate explicitly
   defers this) — documented here as a possible future UX addition, not implemented.
5. The one transient `Hidden import` PyInstaller message (see "Real export evidence" above)
   recurred during this milestone's own rebuild, isolated (no concurrent validation script
   running) — confirmed non-fatal by direct binary smoke test, consistent with M1's own
   finding that this message does not indicate an actual packaging defect.

## M3 handoff

Per the mandate's stop condition (§59): this document does not authorize M3. M3 requires
explicit Project Owner approval after Human Validation of this milestone's fresh `.app`
(§51 checklist, `docs/migration/BUILD-024-M2-HUMAN-VALIDATION.md`, left **PENDING**).

## Gate BUILD-024-M2

**PASS** (engineering). See `scripts/validate-build024-m2.sh` for the automated gate;
final line `BUILD-024-M2 CONSISTENCY GATE: PASS`. Human Validation remains **PENDING**.
