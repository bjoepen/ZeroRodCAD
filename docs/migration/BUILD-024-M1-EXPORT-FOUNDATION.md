# Build 024 M1 — Export Architecture & Contract Foundation

Status: **COMPLETE — Gate BUILD-024-M1: PASS** (see "Known limitations" for the one
qualification, which does not affect the M1 gate itself).

## Objective

Build 024's stated title is "STL / STEP Export Workflow." M1's own scope, per
`docs/migration/BUILD-024-HANDOFF.md` and this milestone's mandate, is narrower: establish how
the existing, already-working engine export capability
(`src/zerorodcad/export.py`'s `export_project`) becomes a safe, explicit, testable Desktop 2.0
capability — the sidecar command, the Rust command boundary, the native-dialog security
boundary, and the empirical facts (timing, overwrite behavior, error modes) any later UI must be
designed against. M1 does not build the final Export button, status panel, or overwrite
confirmation UX — that is M2.

## Inherited capabilities (unchanged, not rewritten)

- `zerorodcad.export.export_project(output_directory, parameters)` — validates parameters,
  lazily imports CadQuery/OCP, and writes `<project>-body.stl`, `<project>-assembly.step`, and
  `<project>-report.md` into a directory. Used exactly as-is.
- The persistent Rust engine manager (`desktop/src-tauri/src/engine.rs`) — `export` is just
  another command through the same `engine::request` entry point already used for `preview`,
  `ping`, `status`, `parameters_defaults`. No process-lifecycle code changed.
- `zerorod-sidecar/v1` (envelope), `zerorod-parameters/v1` (parameter request shape),
  `zerorod-mesh/v1` (untouched — export never touches mesh data) — all three contracts are
  unchanged by this milestone (verified below).
- The frontend's `accepted` parameter state (`parameter_panel.ts`) — already exposes
  `getAccepted()` / `getAcceptedRequest()`, unmodified by this milestone.

## Current engine export behavior (empirically characterized)

`export_project` (`src/zerorodcad/export.py`):

1. Calls `validate_parameters` (raises `ValueError` on domain-invalid input — the exact same
   Level-3 validator `preview` already uses).
2. Lazily imports `cadquery.exporters` and `zerorodcad.model` (kept lazy for packaged-app startup
   latency, unchanged).
3. `directory.mkdir(parents=True, exist_ok=True)`.
4. Computes a filesystem-safe project name (`_safe_name`) and three fixed filenames from it.
5. Exports the STL body, then builds and exports the STEP assembly, then writes the Markdown
   report — always all three, always in that order, always into one directory.

### Output inventory (measured against real canonical defaults)

| File | Role | Measured size |
|---|---|---|
| `cbg-open-g-body.stl` | `body_stl` | 116,984 bytes |
| `cbg-open-g-assembly.step` | `assembly_step` | 105,003 bytes |
| `cbg-open-g-report.md` | `report_markdown` | 668 bytes |

All three confirmed non-empty and valid enough for downstream tooling (STL/STEP round-tripped by
CadQuery's own exporters; the report is valid Markdown text). An alternate parameter set
(`body_width: 38 → 60`) produced STL/STEP files of the **same byte size** (binary STL/STEP have a
fixed per-primitive size; content is not byte-identical) — confirmed via MD5 diff and by grepping
the differing `Body width` value in each report. This is documented so nobody mistakes
"same size" for "export didn't pick up the new parameters" in a future test.

### `report.md`

`zerorodcad.report.build_report` — a Markdown parameter table, string/gauge table, and
validation summary (re-running `validate_parameters` a second time, purely for the report's own
"Validation" section — not a second authority). Always generated as part of `export_project`;
Build 024 does not change or drop it.

## Canonical export-source semantics

**Decision: export always uses the frontend's `accepted` parameter state — not the draft.**
`parameter_panel.ts`'s `accepted` already means "the parameter values currently represented in
the preview, or the last state a completed engine round trip confirmed" (established in Build
023 M4, unchanged here). Nothing in M1 required changing this — `getAcceptedRequest()` already
returns exactly the `zerorod-parameters/v1` envelope `engine_export` expects. A still-debouncing
or locally-invalid draft is never eligible to reach `accepted`, so it can never reach export
either, by construction — no new guard needed. M2 wires the actual Export trigger to
`getAcceptedRequest()`; M1 only had to confirm the plumbing accepts an explicit parameter object
(same shape `engine_preview_mesh_with_parameters` already accepts).

## Export command decision

**Option A (one export action exports the complete project set) is what M1 implements** — it is
the only option `export_project` currently supports without an engine change. `export_project`
always produces STL + STEP + report together, in one call, with no per-format entry point.
Independent STL-only / STEP-only export (Option B) would require splitting `export_project`
internally (exposing `build_body`+STL export and `build_assembly`+STEP export as separately
callable engine operations) — a genuine engine-level change, out of M1's authorized scope ("no
engine rewrite unless a genuine bug is proven"). This is flagged as an explicit, deferred product
decision for a future Build 024 milestone, not silently ruled out.

**Sidecar command:** `export` (new entry in `main.py`'s `COMMANDS` dict, alongside `ping`,
`status`, `preview`, `parameters_defaults`, `shutdown`).

**Rust command:** `engine_export` (new, in `commands.rs`) — follows the established
"new command, not an overloaded flag" pattern (`engine_preview_mesh` /
`engine_preview_mesh_with_parameters` already set this precedent).

### Request/response shape

```jsonc
// request.parameters for the "export" sidecar command:
{
  "parameters": {"schema": "zerorod-parameters/v1", "values": { /* optional, empty = defaults */ }},
  "output_directory": "/Users/example/exports"
}

// success result:
{
  "output_directory": "/Users/example/exports",
  "files": [
    {"role": "body_stl", "filename": "cbg-open-g-body.stl", "path": "/Users/example/exports/cbg-open-g-body.stl"},
    {"role": "assembly_step", "filename": "cbg-open-g-assembly.step", "path": "..."},
    {"role": "report_markdown", "filename": "cbg-open-g-report.md", "path": "..."}
  ],
  "timing": {"export_seconds": 0.13}
}
```

Rust's `engine_export(app, state, parameters: Value, output_directory: String)` wraps these two
into the combined object above and forwards it verbatim through `engine::request(..., "export",
...)` — Rust does not interpret either value, exactly like `engine_preview_mesh_with_parameters`
already does for `parameters`.

## Path semantics

**Directory selection, not file selection** — confirmed both by `export_project`'s own shape (it
always writes a fixed *set* of files into a directory, never a single named output file) and by
the legacy PySide6 reference (`src/zerorodcad_desktop/main_window.py`'s `export_files` uses
`QFileDialog.getExistingDirectory`, not a save-file dialog). Build 024 M1's Rust
`select_export_directory` command uses the same shape (`tauri-plugin-dialog`'s folder picker).

- **Normalization:** whatever the OS dialog returns is forwarded unmodified; no path manipulation
  happens Rust-side.
- **Nonexistent destination:** not an error case — `export_project`'s own `mkdir(parents=True,
  exist_ok=True)` creates it. A native folder picker cannot itself return a nonexistent path
  (it only returns existing, browsable directories), so this only matters for a
  hypothetical future non-dialog entry point, not M1's flow.
- **Cancellation:** see below.

## Dialog cancellation

`select_export_directory` returns `Option<String>` (`Some(path)` / `None`) — cancellation is
`None`, a normal successful return, never a thrown `EngineError`. The frontend (M2) is expected
to treat `null` as "do nothing," not surface any error UI, and never dispatch an `engine_export`
call at all when the user cancels — so cancellation never becomes sidecar-level surface, and
never risks being confused with an export failure.

## Security-boundary delta

**Before (Build 023 baseline):** WebView capability = `["core:default"]` only. No filesystem,
shell, or process permission of any kind.

**After (Build 024 M1):** WebView capability = `["core:default", "dialog:allow-open"]`.

- `tauri-plugin-dialog` (`2.7.2`, current/maintained — confirmed via `cargo add
  tauri-plugin-dialog@2`, resolved against `tauri 2.11.5`) is a Tauri v2-native plugin, added as
  a genuine new Cargo dependency (`desktop/src-tauri/Cargo.toml`) and registered in `lib.rs` via
  `.plugin(tauri_plugin_dialog::init())`.
- Exactly one permission is granted: `dialog:allow-open` (the plugin's folder/file *open* picker
  command). **Not** granted: `dialog:allow-save`, `dialog:allow-message`, `dialog:allow-ask`,
  `dialog:allow-confirm`, or the bundled `dialog:default` (which would include several of those).
  This is the narrowest permission that lets `pick_folder` work.
- `tauri-plugin-dialog` pulls in `tauri-plugin-fs` (`2.5.1`) as a **transitive Cargo dependency**
  (used internally by the dialog plugin's save-file helper, which this app never calls). This is
  a compile-time dependency only — `tauri_plugin_fs::init()` is never called, no `fs:*`
  permission appears in `capabilities/main-capability.json`, and Tauri v2's permission system is
  capability-file-driven: a crate being linked grants nothing by itself. The WebView still cannot
  list a directory, read a file, or write a file directly — it can only ask Rust to show the
  native picker and receive back the one path string the user chose.
- What crosses the boundary: an opaque, user-chosen absolute path string, nothing else. No
  directory contents, no file contents, no read/write capability travels with it — the only thing
  that ever performs a filesystem read/write against that path is the sidecar's `export_project`
  call, which was already trusted with disk access (it is a local Python process, not the
  WebView).
- CSP (`desktop/src-tauri/tauri.conf.json`) is unchanged.

This is the one place Build 024 intentionally expands the security surface, exactly as
anticipated by `BUILD-024-HANDOFF.md` — and the expansion is a single, narrow, auditable
permission grant, not a broad filesystem capability.

## Overwrite discovery (empirical)

Exporting twice into the same directory with the same `project_name` (so the same three
filenames) **overwrites silently, in place** — confirmed via file MD5/content diff and mtime
comparison across two real `export_project` calls. No partial old content remained; each file's
new content fully replaced the old. This matches the legacy PySide6 app's behavior (no
overwrite-detection code exists there either — `QFileDialog.getExistingDirectory` + direct
`export_project` call, same as this milestone's sidecar handler). **Overwrite confirmation UX is
explicitly out of M1's scope** (`BUILD-024-HANDOFF.md`: "a genuine Build 024 product decision")
— M2 must decide whether to warn before overwrite; M1 only establishes that the underlying
behavior is silent-overwrite-in-place, not "refuses," not "appends a suffix."

## Partial-failure discovery (critical finding)

**`export_project` is not reliably erroring on every real failure mode**, discovered by testing
export into a read-only (`0o500`, no write bit) directory:

- `cadquery.exporters.export(...)` (the STL writer) and CadQuery's `Assembly.export(...)` (the
  STEP writer) **silently no-op** on an unwritable directory: no exception raised, no file
  created, execution continues normally.
- `zerorodcad.report.save_report`'s plain `Path.write_text(...)` (the report writer, which runs
  last) correctly raises `PermissionError` in the same situation.

This means `export_project`'s return value (a 3-tuple of paths) cannot be trusted as proof that
all three files were actually written — in a directory permission scenario, it can raise (because
the report write fails), but in principle a scenario exists where STL/STEP silently fail to write
while something else about the directory still allows the report write to succeed, which would
previously have looked like full success. **This is not something M1 is authorized to fix inside
`export_project` itself** (no engine rewrite) — instead, the sidecar's `export` command handler
adds a defensive **post-export verification step**: every expected output file is checked
(`path.is_file() and path.stat().st_size > 0`) after `export_project` returns, before the handler
reports success. A missing/empty file becomes a structured `export_incomplete` error
(`details.missing` lists which role(s) failed) rather than a false "ok": true. This is boundary
code, not an engine change, and is exercised by
`tests/test_zerorod_sidecar_main.py::test_export_permission_denied_directory_returns_structured_error`.

**`export_project` is therefore not transactional** — a scenario where STL succeeds and STEP (or
the report) fails partway through is architecturally possible; the sidecar handler's
post-verification is the only thing standing between that and a false-positive success response
crossing the IPC boundary.

## Error model

Reused from the existing structured envelope, no new protocol — new export-specific `code`
values only where the existing generic ones didn't already cover the failure:

| Code | When | Source |
|---|---|---|
| `invalid_destination` | `output_directory` missing/empty/non-string | new, sidecar |
| `invalid_parameters_domain` | cross-parameter validation failure | reused (same as `preview`) |
| `invalid_parameter_type` | wrong JSON type for a field | reused (same as `preview`) |
| `invalid_parameters` | unknown field / malformed `values` | reused (same as `preview`) |
| `invalid_parameters_schema` | wrong `parameters.schema` | reused (same as `preview`) |
| `export_invalid_destination` | destination path exists as a non-directory (`FileExistsError`) | new, sidecar |
| `export_permission_denied` | a write raised `PermissionError` directly | new, sidecar |
| `export_write_failed` | any other `OSError` during export (e.g. disk full — **unverified**, see below) | new, sidecar |
| `export_incomplete` | `export_project` returned but an expected output file is missing/empty | new, sidecar (the partial-failure backstop above) |
| `export_failed` | any other unexpected exception | new, sidecar (catch-all, never a raw traceback) |

Disk-full was not reproduced (unsafe to simulate reliably in this environment) — `export_write_failed`
is its designed landing code (via the generic `OSError` handler, since `OSError.ENOSPC` is a
subclass of `OSError`), but this specific path is **unverified**, documented as such rather than
claimed tested.

No raw Python traceback crosses the boundary in any tested case (asserted directly in tests).

## Timeout measurement

Measured directly against `.venv`'s real CadQuery/OCP installation (same engine code path the
sidecar uses):

| Scenario | Measured | Note |
|---|---|---|
| First `export_project` call in a fresh process (cold — includes CadQuery's own lazy import) | **1.447 s** | Worst case: nothing warmed the interpreter yet |
| `export_project` after a prior `preview` call already warmed CadQuery (realistic persistent-sidecar case) | **0.130 s** | The sidecar always runs `preview` at least once before most sessions' first export |
| Second `export_project` call, same warm process | **0.132 s** | Steady state |
| `export_project` with alternate parameters (`body_width: 60`), warm process | **0.133 s** | No meaningful geometry-dependent variance observed |
| — breakdown: `build_body` | 0.060 s | |
| — breakdown: STL write | 0.006 s | |
| — breakdown: `build_assembly` | 0.060 s | |
| — breakdown: STEP write | 0.003 s | |
| — breakdown: report write | 0.0001 s | |

**Existing Rust request timeout: 30 s (`engine::REQUEST_TIMEOUT_SECS`, unchanged).**

**Classification: SAFE.** Even the cold-start worst case (1.447 s) leaves a >20x margin under the
30 s timeout; the realistic warm case (~0.13 s) leaves a >200x margin. No evidence supports
changing the timeout, so it is retained unchanged, per the mandate's "evidence-based only" rule
for touching it at all.

## Serialized request queue interaction

No new concurrency code. `export` goes through the exact same `engine::request` entry point,
guarded by the same `Mutex`-held `EngineState`, as every other command. An `engine_export` call
issued while a `preview` request is in flight will simply wait for the mutex like any two
requests already do today — this was true before Build 024 and needed no change. **Chosen
policy:** since export is always sourced from `accepted` (see above), and `accepted` only updates
after a preview round trip *completes*, there is no scenario where export races a still-in-flight
preview for "which parameters win" — by the time `accepted` reflects new values, that preview
request has already finished and released the mutex. M2's UI may still choose to disable the
Export trigger while `livePreviewStatus !== "up-to-date"` purely for UX clarity (avoiding a queued
export that visibly waits), but this is not required for correctness.

## Consistency of what is exported

Because export sources `accepted`, and `accepted` is defined (Build 023 M4) as "reflects the
model currently shown, or the last state a completed round trip confirmed," a still-debouncing or
locally-invalid draft is structurally unreachable as an export input — there is no
edited-but-not-yet-previewed value the export path could ever see. No new guard was needed to
achieve this; it is a consequence of reusing `accepted` rather than reading the live draft.

## `project_name` → filename behavior (empirical)

`export.py`'s `_safe_name`: lowercases, replaces every non-alphanumeric character with `-`,
collapses runs of `-`, strips leading/trailing `-`, and falls back to `"zerorod"` if the result is
empty.

| Input | Filenames produced |
|---|---|
| `"CBG Open G"` (canonical default) | `cbg-open-g-*` |
| `""` (empty) | `zerorod-*` (fallback) |
| `"   "` (whitespace-only) | `zerorod-*` (fallback — `.strip()` empties it first) |
| `"Café/Röd: Test*Name?<>|"` (Unicode + filesystem-invalid characters) | `café-röd-test-name-*` |

Unicode letters with diacritics (`é`, `ö`) are `str.isalnum() == True` in Python and are kept
lowercase as-is — not transliterated to ASCII. Filesystem-invalid characters (`/`, `:`, `*`, `?`,
`<`, `>`, `|`) are all correctly replaced (they are not alphanumeric), so no export ever attempts
to write a path-traversal or invalid-character filename purely from `project_name` content. Two
different project names can collide onto the same safe name (e.g. `"A!B"` and `"A?B"` both
sanitize to `"a-b"`) — this is existing engine behavior, not something M1 changes; combined with
the overwrite-in-place behavior above, two different projects with colliding sanitized names
exported to the same directory would silently overwrite each other. Documented as a known
characteristic, not fixed here (no engine rewrite).

## Real export evidence

- **Sidecar unit tests** (`tests/test_zerorod_sidecar_main.py`, 35 tests total, 14 new): default
  export inventory, JSON-serializability/no-traceback, alternate-parameter geometry difference,
  `project_name` filename shaping, missing/empty `output_directory`, invalid domain parameters,
  invalid field type, unknown field, destination-is-a-file, permission-denied directory,
  overwrite-in-place, valid-after-a-failed-export (sidecar stays usable).
- **Real subprocess, real persistent-loop evidence**
  (`tests/test_zerorod_sidecar_persistent.py::TestRealPersistentSubprocess`, run against the
  TE-001.1-patched, VTK-free `.venv-novtk-poc` interpreter — the same "real, not mocked"
  evidence class Build 022/023 already established as acceptable proof for this repository): a
  single real subprocess is driven through
  `preview → export(defaults) → preview → export(body_width=60) → preview → shutdown` over its
  real stdin/stdout, and: every response is `ok: true`; both exports produce real, non-empty,
  content-different STL/STEP/report files on disk; preview keeps working after each export in the
  same process (no restart); the process exits cleanly (`returncode == 0`) on `shutdown` (no
  orphan).
- **Real productive PyInstaller onedir bundle, rebuilt and smoke-tested**
  (`scripts/validate-build024-m1.sh`'s "Packaging — productive onedir sidecar rebuild" section):
  the exact `.venv-novtk-bundle` + `packaging/tauri/sidecar-onedir.spec` pipeline
  `scripts/build-productive-desktop-app.sh` uses was rebuilt from scratch and driven through
  `preview → export(defaults into a real temp directory) → shutdown` — `preview` and `export`
  both returned `ok: true`, `export` produced 3 real non-empty files on disk, and `shutdown`
  returned cleanly, with 0 orphan processes afterward. This is the literal frozen production
  binary, not `.venv-novtk-poc` — see "Known limitations" below for one earlier, transient
  failure of this same rebuild that turned out not to be a real blocker.
- **Full Python suite**: 238/238 passed (`.venv`), including all pre-existing Build 022/023 tests
  — no regression.
- **Rust suite**: 26/26 passed, including 3 new `protocol.rs` tests proving the exact export
  request/response wire shapes independent of a running app.
- **Frontend suite**: 180/180 passed (12 files), including 5 new `export.test.ts` tests for the
  new `export.ts` protocol-foundation module (types + `selectExportDirectory`/`requestExport`
  thin wrappers — no UI, matching Build 023 M1's own "contract foundation only" precedent for
  `requestPreviewMeshWithParameters`).

## Legacy PySide6 comparison (behavioral reference only)

`src/zerorodcad_desktop/main_window.py`'s `export_files`:

- Trigger: a menu action / toolbar button / sidebar button, all calling the same handler.
- Destination: `QFileDialog.getExistingDirectory` (directory selection — matches M1's choice).
- Cancellation: an empty return value short-circuits with a plain `return` — no dialog, no error.
  Matches M1's `None`-on-cancel design.
- Naming: identical — calls the same `zerorodcad.export.export_project`.
- Overwrite: no overwrite-specific code exists; behavior is whatever `export_project` does
  (silent overwrite, as measured above).
- Status/error handling: a blocking `QMessageBox` on success (lists the created paths) or failure
  (shows the exception string). Build 024's eventual UI (M2) is not obligated to mirror this
  exactly — informs, not binds, the new design, as the same caution Build 023 M1 applied to
  legacy parameter ranges.

No legacy code was ported or modified.

## Contracts — stability confirmed

- `zerorod-parameters/v1`: unchanged (`docs/contracts/ZEROROD-PARAMETERS-V1.md` untouched;
  `export`'s handler reuses `parse_parameters_request` unmodified).
- `zerorod-sidecar/v1`: unchanged (`protocol.py`/`protocol.rs` envelope logic untouched — `export`
  is a new *command name* inside the existing envelope, not a protocol version bump).
- `zerorod-mesh/v1`: untouched (export never produces or consumes mesh data).

## Files changed in M1

- `src/zerorod_sidecar/main.py` — new `_run_export_command`, registered as `"export"`.
- `tests/test_zerorod_sidecar_main.py` — 14 new export tests.
- `tests/test_zerorod_sidecar_persistent.py` — 1 new real-subprocess sequence test.
- `desktop/src-tauri/Cargo.toml` / `Cargo.lock` — new `tauri-plugin-dialog = "2"` dependency.
- `desktop/src-tauri/src/lib.rs` — plugin registration, two new commands registered.
- `desktop/src-tauri/src/commands.rs` — new `select_export_directory`, `engine_export`.
- `desktop/src-tauri/src/protocol.rs` — 3 new tests proving the export wire shape (no logic
  changes — the envelope code was already generic).
- `desktop/src-tauri/capabilities/main-capability.json` — added `dialog:allow-open`.
- `desktop/frontend/src/export.ts` (new) — types + thin `invoke()` wrappers, no UI.
- `desktop/frontend/src/export.test.ts` (new) — 5 tests for the above.

No changes to: `zerorodcad/export.py`, `zerorodcad/model.py`, `zerorodcad/report.py`,
`zerorodcad/parameters.py`, `zerorodcad/validation.py`, `mesh.rs`/`mesh.ts`/`mesh_contract.py`,
`engine.rs` (the export request flows through its existing, unmodified `request` entry point),
`parameter_panel.ts`/`parameter_state.ts` (no UI wiring in M1), `experiments/te002-tauri/`,
`src/zerorodcad_desktop/`.

## Known limitations

1. **One transient PyInstaller onedir bundle-rebuild failure was observed and did not
   reproduce.** Early in this milestone, a manual rebuild of the productive sidecar
   (`.venv-novtk-bundle` + `packaging/tauri/sidecar-onedir.spec`) failed with
   `Hidden import 'OCP.TKernel' not found` / `Hidden import 'cadquery.exporters' not found`.
   That attempt happened shortly after two validation scripts
   (`scripts/validate-build022.sh` and `scripts/validate-build023.sh`) had briefly been run
   concurrently against the same machine-wide PyInstaller code-signing cache
   (`~/Library/Application Support/pyinstaller/bincache*`), and one of those runs itself failed
   with a `SystemError: Failed to process binary ...` from that same cache directory — consistent
   with the hidden-import failure being cache corruption from that collision, not a real defect
   in `.venv-novtk-bundle`'s package set. **This did not reproduce**: the final validation run
   (`scripts/validate-build024-m1.sh`, run in isolation) rebuilt the productive onedir sidecar
   from a clean `--clean` PyInstaller invocation successfully, and the resulting binary was
   smoke-tested end to end (`preview` → real `export` producing 3 non-empty files → `shutdown`,
   0 orphans) — see "Real export evidence" above. No file under `packaging/`, `.venv-novtk-bundle`,
   or the spec was touched by this milestone. Flagged here in case it recurs under concurrent
   validation-script execution — avoid running multiple PyInstaller-building validation scripts
   in parallel on the same machine.
2. Independent STL-only/STEP-only export (Option B, see "Export command decision") is not
   implemented — current `export_project` cannot do it without an engine change.
3. Disk-full (`OSError`/`ENOSPC`) error mapping (`export_write_failed`) is designed but not
   empirically reproduced — documented as unverified, not claimed tested.
4. No export UI exists yet — no button, no status/progress presentation, no overwrite
   confirmation. `export.ts`/`engine_export`/`select_export_directory` are provable, tested, but
   unwired protocol foundation, exactly like Build 023 M1's parameter contract was before M2
   built controls around it.
5. `@tauri-apps/plugin-dialog` (the npm-side JS package) was **not** added to
   `desktop/frontend/package.json` — M1's frontend only calls the Rust command via
   `invoke("select_export_directory")`, which needs no JS-side plugin package (the JS package
   would only be needed for a frontend directly calling the plugin's own JS API, which nothing
   here does). Flagged so M2 doesn't assume it's already available if it turns out to need it for
   something else.

## M2 handoff

**M2: Native Save Dialog & Export Controls.** Owns:

- The actual Export UI trigger (near Apply, operating on `getAcceptedRequest()`).
- Wiring `selectExportDirectory()` → (if non-null) `requestExport()`, both already implemented
  and tested here.
- Status/progress presentation (in-progress, success, structured-error display reusing
  `isEngineError`).
- The overwrite-confirmation product decision this milestone deliberately left open (M1 only
  established that the underlying behavior is silent-overwrite-in-place).
- Deciding whether the export trigger should be disabled while live preview is in flight (not
  required for correctness per "Serialized request queue interaction" above, but may be desired
  for UX clarity).

## Definition of Done — M1 checklist

All items in the mandate's §49 are satisfied, including real end-to-end proof through the actual
productive PyInstaller onedir sidecar binary (not just `.venv-novtk-poc`).

## Gate BUILD-024-M1

**PASS.** The existing engine export is exposed through a clean, tested contract/boundary;
exported-state semantics (`accepted`) are unambiguous and required no new code; real STL + STEP +
report export is proven end-to-end both against a real subprocess (`.venv-novtk-poc`) and against
the actual rebuilt productive PyInstaller onedir binary; timeout/security/filesystem implications
are empirically measured and documented; Build 022/023 functional invariants remain intact (full
regression evidence below). No architecture redesign was required, the existing export engine was
not replaced, and no broad WebView filesystem access was introduced — none of the FAIL conditions
in the mandate's §50 apply.
