# Build 024 M2 — Export Bugfix (Human Validation FAIL → corrected)

## Status

Human Validation of the original Build 024 M2 engineering commit (`31d1d11` /
docs-sync `1a7e722`) found a real, reproducible runtime defect. This document records the
root cause, the fix, why the M2 validation gate did not catch it, and the closed gap.
Engineering is corrected and re-gated **PASS**; Human Validation must be **re-run** against
the fresh build described below — it is not assumed to pass from the fix alone.

## Reported defect

```text
invalid args `outputDirectory` for command `engine_export_preflight`:
command engine_export_preflight missing required key outputDirectory
```

Additionally reported: the target/destination (e.g. a Downloads folder) could not be
selected/used for export in the real app.

## Root cause

`#[tauri::command]`'s **default** argument binding expects the JS `invoke()` payload's keys
in **camelCase**, derived automatically from each Rust parameter name — so a plain
`#[tauri::command]` on a function taking `output_directory: String` requires the frontend to
send `{"outputDirectory": ...}`, not `{"output_directory": ...}`.

`desktop/src-tauri/src/commands.rs`'s `engine_export` and `engine_export_preflight` (Build
024 M1 and M2 respectively) both declared plain `#[tauri::command]` with an
`output_directory: String` parameter. `desktop/frontend/src/export.ts`'s
`requestExport`/`requestExportPreflight` — correctly, matching every other JSON field name
in this app's `zerorod-parameters/v1`/`zerorod-sidecar/v1` contracts, and the very
`"output_directory"` key `engine_export`/`engine_export_preflight` forward to the sidecar two
lines later — sent `{"output_directory": ...}`. Tauri's default camelCase expectation and the
frontend's (correct, contract-consistent) snake_case payload never matched.

**Both commands had the identical defect.** Human Validation happened to surface it via
`engine_export_preflight` (the first of the two called in the real click-through flow, since
`export_panel.ts` always preflights before exporting) — `engine_export` itself was never
reached in that session because the preflight call failed first. This is why "the Download
folder could not be selected/used" and the `outputDirectory` error were **the same underlying
defect**, not two separate bugs: the native directory dialog itself worked correctly (see
"Directory selection was never the problem" below); every directory the user picked
immediately hit the broken `engine_export_preflight` call right after selection.

### Explicitly ruled out (not the cause)

- **Native directory dialog / path type.** `tauri-plugin-dialog`'s `pick_folder` on desktop
  (macOS) always returns `FilePath::Path(PathBuf)` (confirmed by reading
  `tauri-plugin-fs-2.5.1/src/file_path.rs`'s `From<PathBuf> for FilePath` impl, used by
  `tauri-plugin-dialog-2.7.2/src/desktop.rs`'s `pick_folder`), never `FilePath::Url`.
  `select_export_directory`'s `folder.map(|path| path.to_string())` therefore always produces
  a plain OS path string (`p.display()`), never a `file://` URI. `select_export_directory`
  itself takes no arguments beyond `AppHandle`, so it was never susceptible to this class of
  defect in the first place.
- **`export_project`/engine logic.** Untouched; this is purely an IPC argument-binding
  defect at the Desktop/Tauri integration boundary.

## Fix

`#[tauri::command(rename_all = "snake_case")]` added to both `engine_export` and
`engine_export_preflight` (`desktop/src-tauri/src/commands.rs`). This makes Tauri's argument
binding match the app's one existing wire convention (snake_case, used everywhere else in
this app's contracts) instead of introducing a second, camelCase-only convention at just this
one boundary. No frontend change was needed or made — `export.ts` already sent the
contract-consistent shape; only the previously-mismatched Rust side needed correcting.

One canonical invocation shape is now locked down by tests (see below) — no aliasing, no
dual camelCase/snake_case acceptance.

### Why not fix it the other way (camelCase in the frontend)?

Considered and rejected: `engine_export`'s own body immediately re-serializes
`output_directory` into the exact JSON object forwarded to the sidecar
(`serde_json::json!({"parameters": parameters, "output_directory": output_directory})`) —
switching the frontend to `outputDirectory` would introduce a *second* naming convention at
the IPC-argument layer only, immediately translated back to snake_case one line later in
Rust. Fixing the Rust attribute instead keeps exactly one convention (snake_case) end to end:
`export.ts` → `engine_export`'s IPC arguments → the JSON forwarded to the sidecar → the
sidecar's own JSON response fields (`output_directory`, `expected_files`, etc.) — all
snake_case, unchanged, no drift anywhere in the pipeline.

## End-to-end path flow (traced and verified)

```text
click "Export Model…"
    -> selectExportDirectory() -> invoke("select_export_directory")   [no args; unaffected]
    -> native macOS directory picker (tauri-plugin-dialog, pick_folder)
    -> FilePath::Path(PathBuf) -> .to_string() -> plain OS path string (verified: no file:// URI)
    -> requestExportPreflight(values, directory)
       -> invoke("engine_export_preflight", { parameters, output_directory: directory })
       -> ✅ now accepted (rename_all = "snake_case")
    -> conflict result (has_conflicts / conflicts[])
    -> [confirm_overwrite if conflicts, else straight through]
    -> requestExport(values, directory)   [same `directory` value, never re-derived]
       -> invoke("engine_export", { parameters, output_directory: directory })
       -> ✅ now accepted (rename_all = "snake_case")
    -> engine::request(..., "export", {"parameters":..., "output_directory": directory})
    -> sidecar `_run_export_command` -> export_project(directory, params)
```

The same `directory` value (the exact string `selectExportDirectory()` returned) flows
unmodified through preflight and export — `export_panel.ts` holds it in one place
(`ExportPanelState`'s `confirm_overwrite.outputDirectory` / the `directory` local in
`handleExportClick`/`runPreflightThenExport`/`runExport`) and never re-derives or re-prompts
for it between the two calls. No separate/stale path state exists.

## Regression tests added

**Rust** (`desktop/src-tauri/src/commands.rs`, `mod ipc_argument_binding`) — dispatches a
real IPC request through Tauri's actual generated command deserializer
(`tauri::test::get_ipc_response`), not a mocked helper one layer below the invoke() call:

- `accepts_the_exact_payload_export_ts_sends_for_preflight_and_export` — the literal
  `{"parameters": ..., "output_directory": ...}` shape `export.ts` sends is accepted.
- `rejects_camel_case_output_directory` — the shape Tauri's *default* binding would have
  required (`outputDirectory`) is now explicitly rejected, locking down the one canonical
  invocation shape.
- `rejects_a_missing_output_directory` — a missing key is rejected (sanity check on the
  discriminator these tests use).

These tests dispatch a local twin command (`export_args_binding_twin`) carrying the exact
same `#[tauri::command(rename_all = "snake_case")]` attribute and the exact same
`(parameters: Value, output_directory: String)` parameter list as both real commands, rather
than the literal production functions — `engine_export`/`engine_export_preflight` take
`app: AppHandle`, which (like every command in this file) resolves to the concrete
`AppHandle<Wry>`, and `tauri::test::get_ipc_response` requires `MockRuntime`; making them
generic over `Runtime` purely for testability would require also making `engine.rs` generic
(it takes `&AppHandle` concretely throughout), which is a real architectural change well
outside a narrow argument-binding bugfix and would touch `engine.rs`, an invariant this
repository's own validation gates explicitly check as unchanged across builds. The twin
command exercises the exact mechanism that broke (the macro attribute + parameter name/type
combination) through the real IPC dispatch path, honestly documented as a twin rather than
overclaiming it as literally the production command.

**Verified to actually catch the reported bug class**: temporarily reverting
`export_args_binding_twin`'s attribute back to plain `#[tauri::command]` reproduced the exact
reported error shape —
`"invalid args \`outputDirectory\` for command \`export_args_binding_twin\`: command
export_args_binding_twin missing required key outputDirectory"` — confirming the test would
have failed against the original defective code, then re-applying the fix made it pass again.

## Validation-gate blind spot — also fixed

`scripts/validate-build024-m2.sh` reported `BUILD-024-M2 CONSISTENCY GATE: PASS` despite this
real defect because **nothing in the gate ever dispatched a real IPC request through the
Rust/Tauri command-argument-binding layer**:

- The frontend test suite mocks `@tauri-apps/api/core`'s `invoke()` entirely — it proves what
  `export.ts` *sends*, never what Tauri's generated deserializer *accepts*.
- The gate's packaging smoke test drives the real onedir sidecar binary's stdin/stdout
  **directly** — it never goes through `invoke()` → the Rust command layer →
  `engine::request` at all, so it structurally cannot exercise (or catch a defect in) that
  boundary.

The script now has a dedicated section, "Rust — real IPC argument-binding regression," that:

1. Asserts the three `ipc_argument_binding` tests above actually ran (not merely that
   `cargo test` as a whole passed, which would also be true if the module were silently
   excluded from compilation).
2. Statically greps that both `engine_export` and `engine_export_preflight` carry
   `rename_all = "snake_case"`.
3. Statically greps that `export.ts`'s two `invoke()` calls use the `output_directory` key.

Its packaging-smoke-test section now carries an explicit comment stating what it does *not*
cover (the IPC argument-binding layer), so this gap cannot silently reappear as "the
packaging test already covers export end to end" in a future reader's assumption.

## Real evidence after the fix

- `cargo test`: 31/31 passed (28 pre-existing + 3 new `ipc_argument_binding` tests).
  `cargo fmt --check` / `cargo clippy --all-targets -- -D warnings`: clean.
- Full Python suite: 338 passed, 1 skipped (pre-existing, unrelated). Ruff clean.
- Frontend: 204 passed (vitest), TypeScript clean, production build clean.
- `scripts/validate-build024-m2.sh`: **`BUILD-024-M2 CONSISTENCY GATE: PASS`**, including the
  new IPC argument-binding section.
- Fresh productive onedir sidecar rebuilt and smoke-tested directly (preview → preflight →
  export → shutdown, all `ok: true`, 3 real non-empty files) — this proves the Python side
  again but, per the blind-spot note above, does **not** by itself prove the Rust IPC
  argument-binding fix; that's what the new Rust tests are for.
- Fresh release `.app` built from the corrected HEAD: 299,736,337 bytes / 285.9 MiB / 201
  files / 57 dirs / 77 symlinks — unchanged from the pre-bugfix measurement (the fix is a
  macro-attribute change, no new dependency, no size impact).
- 0 orphan `zerorod-engine` processes after the full validation run.

## What real GUI click-through this fix cannot itself prove

No display/GUI access is available in this environment, so the actual native macOS directory
dialog interaction, and the full visual "click Export → pick a folder → see success" flow,
were not and cannot be driven end-to-end here. The Rust-level regression tests prove the
*mechanism* (argument binding) that broke is fixed and locked down; only a human,
re-clicking through the fresh `.app` below, can confirm the full real flow now works as
experienced by a user — which is exactly why Human Validation must be **re-run**, not assumed
passing from this fix.

## Human Validation artifact

```text
Absolute path: /Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app
Open command:  open "/Users/bernd/Projekte/ZeroRodCAD-App/desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app"
```

See `docs/migration/BUILD-024-M2-HUMAN-VALIDATION.md` (updated) for the retest checklist.

## Files changed in this bugfix

- `desktop/src-tauri/Cargo.toml` — `tauri` added under `[dev-dependencies]` with the `test`
  feature (test-only; production `[dependencies]` `tauri` entry unchanged, no capability/
  runtime change).
- `desktop/src-tauri/src/commands.rs` — `rename_all = "snake_case"` added to `engine_export`
  and `engine_export_preflight`; new `ipc_argument_binding` test module.
- `scripts/validate-build024-m2.sh` — new "Rust — real IPC argument-binding regression"
  section; clarifying comments on the packaging smoke test's scope.
- `docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md` (this file, new).
- `docs/migration/BUILD-024-M2-HUMAN-VALIDATION.md` — defect recorded honestly, retest items
  added.

No changes to: `export.ts` (frontend), `export_panel.ts`, any Python file, `engine.rs`,
`main-capability.json` (security capability unchanged — this was never a security-boundary
issue), the legacy PySide6 app, `experiments/`.

## Stop condition

Per the bugfix mandate: engineering is corrected and gated PASS. **Do not start M3.** Await
Project Owner re-validation of the fresh `.app` above.
