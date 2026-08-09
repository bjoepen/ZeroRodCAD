# Build 022 — Milestone 2: Productive Sidecar & Rust Lifecycle

Status: **COMPLETE**

## Objective

Carry the Python-sidecar and Rust-process architecture proven in TE-002 / TE-002.1 / TE-002.2B
into the productive ZeroRodCAD Desktop 2.0 path established by M1. At the end of this milestone,
the productive Tauri application can reliably start a persistent Python 3.13 sidecar, talk to it
over a structured stdin/stdout protocol, reuse it across requests, handle failures in a controlled
way, and shut it down cleanly on app exit.

Not implemented in M2 (per the mandate and per `docs/migration/README.md`'s build sequence):
Three.js rendering, `BufferGeometry`, parameter UI, live preview, STL/STEP UI, feature parity,
PySide6 removal. M3 owns the actual 3D preview.

## Sidecar architecture

```text
WebView / Frontend
    │  invoke("engine_ping" | "engine_sidecar_status" | "engine_preview" | "engine_shutdown")
    ▼
Rust Process / IPC Layer  (desktop/src-tauri/src/engine.rs, protocol.rs, mesh.rs, commands.rs)
    │  private stdin/stdout, zerorod-sidecar/v1 JSON
    ▼
Persistent Python 3.13 Sidecar  (src/zerorod_sidecar/)
    │
    ▼
ZeroRodCAD Engine (unchanged) → CadQuery + cadquery-ocp-novtk
```

Rust owns spawn, lifecycle, IPC, timeout, crash detection, restart, and shutdown/cleanup, exactly
as `ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`'s security boundary requires. The frontend never
touches a process or shell API directly — its only surface is five narrow, app-registered Tauri
commands (`app_info`, `engine_status`, `engine_ping`, `engine_sidecar_status`, `engine_preview`,
`engine_shutdown`), all under the `core:default` capability.

## Productive paths

- `src/zerorod_sidecar/` — the productive Python sidecar package: `protocol.py`
  (`zerorod-sidecar/v1` envelope), `mesh_contract.py` (`zerorod-mesh/v1` transport), `main.py`
  (command dispatch + persistent loop), `__main__.py` (entry point).
- `desktop/src-tauri/src/protocol.rs` — the Rust side of the same envelope: request-id generation,
  request-line building, response parsing.
- `desktop/src-tauri/src/mesh.rs` — Rust-side `zerorod-mesh/v1` validation + summarization.
- `desktop/src-tauri/src/engine.rs` — the persistent engine manager: spawn, reuse, timeout, crash
  detection, restart-once, shutdown, non-blocking status.
- `desktop/src-tauri/src/commands.rs` — the five Tauri commands the WebView actually calls.
- `packaging/tauri/sidecar-onedir.spec` — the productive PyInstaller spec (onedir, TE-002.2B
  excludes).

**Not used, and not modified:** `tools/poc/tauri/sidecar/`, `experiments/te002-tauri/`. Those stay
the research/regression reference; the productive code above adopts their proven principles without
being built on top of them directly (`ADR-022-001` / `docs/migration/README.md`, "Reference
implementation policy").

## Process lifecycle

### Lazy vs. eager start — decision: **lazy**

The sidecar is not started when the app launches. It starts on the first `engine_ping` /
`engine_sidecar_status` / `engine_preview` call (`engine::ensure_started`, called from
`engine::request`). No product requirement in this milestone needs the engine warm before a user
does anything with it, and lazy start means an app that's merely opened and left idle never pays
the ~0.6 s cold-start cost or holds a ~320 MB resident sidecar process for no reason. This mirrors
the mandate's own stated preference ("Bevorzugung: lazy start, wenn kein Produktgrund dagegen
spricht") — no product reason against it was found.

### Full lifecycle, as implemented

```text
app starts
    ↓
sidecar not started (EngineState::default() — engine: None)
    ↓
first engine_ping / engine_sidecar_status / engine_preview call
    ↓
RunningEngine::spawn() — resolves the bundled onedir sidecar via Tauri's resource API,
                         spawns it through tauri_plugin_shell, stores child + pid
    ↓
request sent, response awaited (30 s timeout), request_id + schema validated
    ↓
process remains alive — subsequent calls reuse it (guard.is_some() short-circuits re-spawn)
    ↓
[if a request times out or the process is detected terminated:]
    kill the dead engine → spawn a fresh one → retry the same command exactly once
    ↓
explicit engine_shutdown, OR app exit (RunEvent::ExitRequested)
    ↓
graceful shutdown attempt (send "shutdown", wait up to 5 s) → forced kill if that doesn't finish
    ↓
process exits
    ↓
0 orphan processes (verified — see "Real app validation" below)
```

## Protocol

`zerorod-sidecar/v1` adopted stable, unmodified from `docs/research/TE-002-Tauri-ThreeJS/Sidecar-Contract.md`:
one JSON request per stdin line, one JSON response per stdout line. `stderr` carries diagnostics
only; `stdout` never carries anything else (verified — see "Tests").

## Commands

| Sidecar command | Purpose | Rust-side caller |
|---|---|---|
| `ping` | Liveness check, returns `{status, pid}` | `engine_ping` |
| `status` | Richer diagnostics: Python/CadQuery version, OCP variant, `vtk_installed`, milestone | `engine_sidecar_status` |
| `preview` | Real ZeroRod mesh, default parameters only (parametrized requests rejected with `unsupported_parameters`, same PoC-scope limit as TE-002/TE-002.1) | `engine_preview` |
| `shutdown` | Graceful stop | `engine_shutdown` (and the app-exit handler) |

Rust also exposes `engine_status`, which is **local-only** — it reads Rust's own lifecycle state
(`Stopped`/`Running`/`Error` + last error + pid) without any IPC round trip, so the frontend can
show a status row instantly even while a slow request holds the engine's lock.

## Error model

Every sidecar error is `{code, message}` — never a raw Python traceback (verified:
`test_response_never_contains_traceback_text`). Rust wraps every failure mode in the same
`EngineError {code, message}` shape, including ones the sidecar itself never produces:
`sidecar_missing` (resource resolution failed), `spawn_failed`, `stdin_write_failed`, `timeout`,
`sidecar_crashed`, `invalid_json`, `invalid_schema`, `request_id_mismatch`, `missing_result`, and
`invalid_mesh` (Rust-side mesh-contract validation failure). The frontend's `isEngineError()` type
guard and every UI error path handle this uniformly.

## Timeout

30 seconds (`engine::REQUEST_TIMEOUT_SECS`), carried over unchanged from TE-002/TE-002.1's own
value — no evidence in this milestone suggested a different number, and the mandate explicitly
allows reusing it without new evidence ("Kein aggressiver produktiver SLA").

## Crash detection & restart

`RunningEngine::send()` distinguishes three outcomes: a normal response, a timeout, and a detected
process termination (`CommandEvent::Terminated` observed before any response line arrived). The
latter two are both treated as "the engine is dead" by `engine::request()`, which kills the dead
handle, spawns a fresh one, and retries the **same command exactly once** — no unbounded retry
loop, matching TE-002.1's own "ein expliziter Retry kann genügen" policy. No `panic!` anywhere in
this path; every failure is a typed `Result`.

Verified directly (not just by code inspection): the real bundled sidecar binary was started, sent
a real `ping`, and then killed with `SIGKILL` from outside the process to simulate an unexpected
crash. Confirmed: the process was gone immediately afterward with no zombie and no orphan — the
same onedir-has-no-forked-worker property TE-002.1's `Process-Lifecycle.md` documented for the
proof-of-concept binary now confirmed for the productive one.

## Shutdown

Two paths, both exercised:

1. **Explicit** (`engine_shutdown` command): sends `shutdown`, waits up to 5 s for the process to
   exit on its own, force-kills if it doesn't.
2. **App exit** (`RunEvent::ExitRequested` in `lib.rs`): calls `engine::kill_if_running`, a
   synchronous, non-blocking best-effort kill — deliberately not the graceful async path, because
   Tauri's exit-event closure isn't async. This is the same simplification TE-002.1's own
   `persistent.rs` made (`kill_if_running` on exit, not a full graceful round trip), reused rather
   than reinvented. The explicit command remains the graceful path for a frontend that wants one.

No onefile fallback exists in the productive sidecar to reintroduce the orphan-process risk onedir
was chosen to avoid (`ADR-022-001`, "Sidecar runtime strategy").

## No-VTK validation

- Static: `find` over the built onedir sidecar for `*vtk*`/`*IVtk*` — 0 hits (the one apparent
  match, `cadquery_ocp_novtk-*.dist-info`, is the OCP variant's own package-metadata directory,
  correctly named, not VTK content).
- Runtime, real subprocess, TE-001.1-patched interpreter (`.venv-novtk-poc`):
  `test_real_subprocess_no_vtk_or_pyside6` — 0 `vtk`/`vtkmodules` modules in `sys.modules` after a
  full `preview` request.
- The sidecar's own `status` command reports `vtk_installed` and `ocp_variant` at runtime from
  `importlib.metadata` — confirmed `vtk_installed: false`, `ocp_variant: "cadquery-ocp-novtk"` when
  queried against the real bundled binary.
- `VTKImportBlocker` (TE-001) is installed before the first `cadquery` import in the productive
  sidecar too — reused verbatim, not reimplemented, as an active safety net (not just a passive
  check) against any future accidental VTK import.

Note: the default `.venv` this repository's own top-level `pytest`/`ruff` commands run under
legitimately has VTK and full `cadquery-ocp` installed (it also serves the legacy PySide6 app —
see `README.md` "Aktueller Stand"). `test_status_returns_engine_and_build_milestone_info` reports
whatever the actual interpreter has rather than hard-coding a No-VTK assumption; the No-VTK
*invariant* is what `TestRealPersistentSubprocess` proves, against the correct (patched, VTK-free)
interpreter.

## No-PySide6/Qt validation

- Same real-subprocess test confirms 0 `pyside6` modules in `sys.modules`.
- The productive sidecar's dependency surface (`src/zerorod_sidecar/`) imports only `zerorodcad.*`,
  stdlib, and (transitively) CadQuery/OCP — no PySide6/Qt import anywhere in the package.
- `packaging/tauri/sidecar-onedir.spec` excludes `PySide6` explicitly, matching TE-002.2B.
- Frontend (`desktop/frontend/`): no Qt/PySide dependency of any kind — it's TypeScript + Vite +
  `@tauri-apps/api`.
- The legacy PySide6 app (`src/zerorodcad_desktop/`) is untouched and still exists in the
  repository, exactly as `ADR-022-001` requires at this stage.

## Performance

Measured with the existing `tools/poc/tauri/benchmark_sidecar_runtime.py persistent` tool (reused
unmodified — same methodology TE-002.1/TE-002.2B used), pointed at the productive onedir build:

| Metric | Build 022 M2 (productive) | ADR-022-001 / TE-002.2B reference | Delta |
|---|---:|---:|---:|
| Cold start | 0.614 s | ~0.612 s | +0.002 s (no regression) |
| Warm median | 0.123 s | ~0.121 s | +0.002 s (no regression) |
| Warm p95 | 0.125 s | 0.1228 s (TE-002.2B) | +0.002 s (no regression) |

**A methodology note, recorded because it's real and worth knowing for future benchmark runs:** the
very first benchmark invocation immediately after a fresh `pyinstaller` build measured a 23.9 s
"cold start" — not a regression, but the OS file cache being genuinely cold for ~268 MB of
just-written files. Re-running the identical benchmark immediately afterward (files now in page
cache) produced the 0.614 s figure above. Anyone re-measuring this after a clean build should expect
the same one-time effect and not mistake it for a real regression.

## Memory

Same tool, RSS via `ps` on the deepest live process descendant (unchanged methodology):

| Checkpoint | Build 022 M2 | TE-002.2B reference | Delta |
|---|---:|---:|---:|
| after request 1 | 319,648 KB | 321,056 KB | −1,408 KB |
| after request 5 | 320,176 KB | 321,408 KB | −1,232 KB |
| after request 10 | 320,512 KB | 321,680 KB | −1,168 KB |
| after request 20 | 320,688 KB | 321,904 KB | −1,216 KB |

No regression — consistently slightly lower, plausibly noise-level (different machine state,
same order of magnitude), not claimed as a real improvement from a single run.

## Packaging note (explicitly deferred to M4, not hidden)

The raw onedir sidecar directory is 268 MB / 197 files — close to TE-002.2B's ~280.27 MiB / 193
file reference. The **real `.app` bundle** produced by `tauri build`, however, measured 399 MB —
because Tauri's own resource-copy step dereferences PyInstaller's dedup symlinks for OpenCASCADE's
dylibs, the exact mechanism TE-002.2B's "Optimization B" diagnosed and fixed with a post-bundle
dedup script. The mandate for this milestone (section 27/28) explicitly scopes the full app-bundle
dylib-dedup fix to **M4** ("wird spätestens in M4 vollständig als App-Bundle-Thema validiert") and
only requires M2 not to introduce a *new*, previously-unknown bad configuration. This is the
already-known, already-diagnosed TE-002.2B gap reappearing in the productive path, not a new one —
recorded here so M4 has the concrete number (399 MB) to fix against, not rediscovered from scratch.

## Tests

- **Rust**: 21 tests (`cargo test`) — `protocol.rs` (8: request-id, request-line, response parsing
  including request_id mismatch, wrong schema, missing result, malformed error object),
  `mesh.rs` (7: valid payload, wrong schema, empty meshes, non-multiple-of-3 positions,
  out-of-range index, NaN positions, missing bounds), `engine.rs` (4: line-extraction buffer
  logic, fresh-state status), `commands.rs` (1: `app_info`, updated to report M2, first added in
  M1). `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings` both clean.
- **Python**: 41 tests across 4 files — `test_zerorod_sidecar_protocol.py` (11),
  `test_zerorod_sidecar_mesh_contract.py` (9, including two that exercise the real ZeroRodCAD
  engine, not fixtures), `test_zerorod_sidecar_main.py` (11, including the response-never-contains-
  traceback and deterministic-shape checks), `test_zerorod_sidecar_persistent.py` (10, 7 in-process
  + 3 real-subprocess against `.venv-novtk-poc`).
- **Frontend**: 17 tests (`vitest run`) — 6 carried over from M1 (`status.test.ts`), 11 new
  (`engine.test.ts`: `isEngineError` type guard, `fetchEngineStatus`, `pingEngine`
  success/`sidecar_missing`/`timeout`, `fetchSidecarStatus`, `requestPreviewSummary`
  success/`invalid_mesh`, `shutdownEngine`). TypeScript (`tsc --noEmit`) and production build both
  clean.
- **Full repository regression**: `pytest -q` — 282 passed, 1 skipped (pre-existing, unrelated:
  `tests/poc/novtk/test_checkpoints_integration.py`'s Gate A re-evaluation note, not touched by
  this milestone).
- **Integration** (real bundled binary, real protocol, no mocking): 5-request round trip
  (ping/status/preview×2/shutdown) against the actual `packaging/tauri/sidecar-onedir.spec` output,
  and again against the *exact* binary copied into a real `.app`'s `Resources/` — both fully
  successful, `vtk_installed: false` confirmed inside the frozen bundle.

## Real app validation

A real debug `.app` was built with the sidecar bundled as a Tauri `resources` entry (not
`externalBin`, which only supports single-file sidecars — same reasoning as TE-002.1) and launched
for real:

```text
desktop/src-tauri/target/debug/bundle/macos/ZeroRodCAD.app
```

Confirmed by screenshot (not assumed): the window opens, shows the M2 status panel and its three
action buttons, with the correct pre-interaction state — Desktop shell READY, Rust bridge READY
(real `app_info` data, "M2"), Python sidecar STOPPED, CAD engine NOT_READY, 3D preview
NOT_IMPLEMENTED (M3). After quitting the app, a process check confirmed 0 remaining
`zerorod-desktop`/`zerorod-engine` processes.

## Known limitation — interactive click-through

Exactly like TE-002 through TE-002.2B before it, this environment cannot automate real WebView
interaction: macOS Accessibility permission is not granted here, confirmed directly (`osascript
'tell application "System Events" to click at {x,y}'` fails with error -25211, "not authorized to
send keystrokes"), not assumed from a prior TE's note. This means the three buttons
("Start / Check Engine", "Ping Engine", "Request Preview Data") were not clicked by an automated
agent in this environment. What *is* automated evidence: the exact bundled sidecar binary answering
every command those buttons would trigger, over the real protocol, including a real crash
simulation — the same "prove the exact artifact through the real protocol" bar TE-002.1 set for
itself. The remaining gap (an actual human clicking those three buttons) is exactly what
`docs/migration/BUILD-022-M2-HUMAN-VALIDATION.md` exists to close, following the same
`HUMAN-VALIDATION.md` pattern TE-002.1/TE-002.2B already established. Not yet filled in by a human
tester — left honestly blank, not fabricated.

## Reproducing the build

```bash
# 1. Build the productive onedir sidecar (reuses the TE-001.1-patched,
#    TE-002.2B-configured .venv-novtk-bundle — no new environment).
.venv-novtk-bundle/bin/pyinstaller --noconfirm --clean \
  --distpath desktop/sidecar-dist --workpath build/zerorod-engine \
  packaging/tauri/sidecar-onedir.spec

# 2. Stage it where tauri.conf.json's bundle.resources expects it.
rm -rf desktop/src-tauri/resources/zerorod-engine-onedir
cp -R desktop/sidecar-dist/zerorod-engine desktop/src-tauri/resources/zerorod-engine-onedir

# 3. Build the app.
cd desktop/src-tauri && ../frontend/node_modules/.bin/tauri build --debug
```

Both `desktop/sidecar-dist/` and `desktop/src-tauri/resources/` are gitignored — they are build
output, not source, exactly like `experiments/*/src-tauri/resources/` already was for the PoC.

## Explicit negative assertions (per the mandate)

- Three.js ZeroRod renderer: **NOT IMPLEMENTED** (M3).
- Parameter UI: **NOT IMPLEMENTED** (Build 023).
- Export UI: **NOT IMPLEMENTED** (Build 024).
- PySide6 removal: **NOT PERFORMED**.
- VTK in the productive sidecar: **0** (static + runtime, verified above).
- PySide6/Qt in the productive Tauri runtime: **0** (verified above).

## Next milestone

**Build 022 / Milestone 3 — Three.js Preview Foundation.** M1 gave the productive app a shell and
an IPC bridge; M2 gave it a real, persistent engine with a proven lifecycle. M3 is what actually
draws the model the engine already proves it can produce.
