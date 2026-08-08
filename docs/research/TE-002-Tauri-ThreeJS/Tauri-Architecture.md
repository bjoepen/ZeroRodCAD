# TE-002 — Tauri Architecture

## The chain, as actually implemented

```
Three.js BufferGeometry (frontend/src/mesh.js, scene.js)
        ^
        | zerorod-mesh/v1 JSON (Mesh-Contract.md)
        |
invoke("request_preview")  — the ONLY IPC call the WebView ever makes
        |
Rust command src-tauri/src/sidecar.rs::request_preview()
        |  — spawns, writes stdin, awaits with timeout, parses response
        v
tauri-plugin-shell (ShellExt::sidecar) — spawns the externalBin
        |
Python sidecar (tools/poc/tauri/sidecar/, built via PyInstaller onefile)
        |  — VTKImportBlocker installed before any cadquery import
        v
zerorodcad.preview.build_preview_scene() -> zerorodcad Engine
        |
CadQuery 2.8.0 + TE-001.1 patch + cadquery-ocp-novtk 7.9.3.1.1
```

## Design decision: process control lives entirely in Rust, not JS

Initially prototyped with the frontend calling `@tauri-apps/plugin-shell`'s `Command.sidecar()`
directly (spawn + write + listen for events). Deliberately changed to a custom
`#[tauri::command] async fn request_preview(app: AppHandle)` that does the spawn/write/timeout/
parse entirely in Rust, and removed `@tauri-apps/plugin-shell` from the frontend dependencies
entirely. Reasons:

1. **Smaller WebView-facing capability surface** (section 28). With the JS-driven design,
   `capabilities/main-capability.json` needed `shell:allow-spawn`, `shell:allow-kill`, and
   `shell:allow-stdin-write` — i.e. the WebView itself held permission to spawn a process, even if
   scoped to one named sidecar. With the Rust-driven design, the WebView holds **zero**
   shell/process permissions — `app.shell().sidecar(...)` is called from trusted Rust code, which
   is not subject to the WebView-facing IPC permission system at all. The final capability file is
   just `["core:default"]`.
2. **Matches section 17 literally**: "Frontend darf nie direkt Python-Prozesse starten.
   Prozesskontrolle gehört in die Tauri/Rust-Schicht." Even though `Command.sidecar().spawn()`
   from JS is still IPC-mediated and capability-gated (Tauri's standard, documented, secure sidecar
   pattern), moving the actual protocol logic (timeout, response parsing, error mapping) into Rust
   makes the "process control belongs in Rust" boundary unambiguous rather than a matter of
   interpretation.
3. **Matches section 30's explicit Rust-test expectations.** With protocol logic in Rust, the
   request/response/error/malformed-JSON/timeout logic is directly unit-testable in Rust
   (`cargo test`, 10 tests, all passing) rather than living only in JS where it would need a
   Tauri-mocking layer to test meaningfully.

This is presented as a design decision made *during* TE-002, not a mistake to hide — the
dependency-governance record in `Dependencies.md` documents `@tauri-apps/plugin-shell` being added
and then removed for exactly this reason.

## Rust sidecar bridge (`src-tauri/src/sidecar.rs`)

- `build_request_line(request_id) -> String` — pure, builds the exact JSON + `"\n"` line.
- `new_request_id() -> String` — nanosecond-timestamp-based, no new crate (`uuid` was considered
  and rejected as unnecessary — see `Dependencies.md`'s stdlib-first preference).
- `parse_response(stdout, expected_request_id) -> Result<Value, PreviewError>` — pure, the same
  validation chain described in `Sidecar-Contract.md`, no process/IO involved (this is what makes
  it unit-testable without spawning anything).
- `request_preview(app) -> Result<Value, PreviewError>` — the actual `#[tauri::command]`: spawns
  via `app.shell().sidecar(SIDECAR_NAME)`, writes the request line, drains `CommandEvent::Stdout`/
  `Stderr`/`Terminated`/`Error` under a `tokio::time::timeout(30s, ...)`. On timeout: `child.kill()`
  then returns `PreviewError{code: "timeout", ...}`. On nonzero exit: `PreviewError{code:
  "nonzero_exit", ...}` including the captured stderr. Otherwise: `parse_response(...)`.

### Rust test coverage (section 30, `cargo test`, 10/10 passing)

`build_request_line_has_expected_shape`, `new_request_id_is_non_empty_and_varies`,
`parse_response_accepts_valid_ok_response`, `parse_response_rejects_empty_stdout`,
`parse_response_rejects_multiple_lines`, `parse_response_rejects_invalid_json`,
`parse_response_rejects_wrong_schema`, `parse_response_rejects_request_id_mismatch`,
`parse_response_surfaces_sidecar_error_response`, `parse_response_rejects_ok_without_result`.

Process-level behaviors mandated by section 30 (nonzero exit, timeout, process cleanup) are
implemented in `request_preview()`'s control flow (kill-on-timeout is unconditional and not
gated on any success path) but were *not* independently re-tested via a fragile spawned-process
Rust integration test — the equivalent process-level behavior (nonzero exit code, timeout,
successful termination) was instead verified directly against the real compiled sidecar binary
from the Python/shell side (`Sidecar-Contract.md`, `Runtime-Validation.md` — the same binary, same
process-lifecycle guarantees, exercised from a simpler harness). This is a deliberate scope choice,
not an oversight — see `Results.md`'s "what was and wasn't verified" section.

## Capabilities (`src-tauri/capabilities/main-capability.json`)

```json
{
  "identifier": "main-capability",
  "windows": ["main"],
  "permissions": ["core:default"]
}
```

That's the entire permission set. No `shell:*` permission anywhere in a WebView-facing capability
file. CSP: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'
data:; connect-src 'self' ipc: http://ipc.localhost` — restrictive, no remote origins, no
`dangerousRemoteDomainIpcAccess`.

## Sidecar packaging

Built via PyInstaller (reusing `.venv-novtk-bundle` from TE-001.2 — same TE-001.1-patched
`cadquery`, same `cadquery-ocp-novtk`, already provisioned, not recreated) from
`tools/poc/tauri/sidecar.spec` into `experiments/te002-tauri/src-tauri/binaries/
zerorod-engine-aarch64-apple-darwin`. **Onefile mode** — one important, real consequence of this
choice is documented in `Performance.md` (startup latency from self-extraction). Declared in
`tauri.conf.json` as `bundle.externalBin: ["binaries/zerorod-engine"]`.

## Frontend (`experiments/te002-tauri/frontend/`)

Vanilla JS + Vite + Three.js — no framework (React/Vue/etc.) added, per "möglichst wenige neue
Dependencies." Three files carry all the logic: `mesh.js` (pure mesh-contract → BufferGeometry
conversion + validation, section 19-20), `scene.js` (camera/renderer/controls/lights/resize/
camera-fit, section 19-20), `sidecar.js` (the one `invoke("request_preview")` call plus error
mapping, section 17-18), wired together in `main.js` with UI states `idle`/`loading`/`ready`/
`error` (section 22) — no `alert()` anywhere, not even temporarily.
