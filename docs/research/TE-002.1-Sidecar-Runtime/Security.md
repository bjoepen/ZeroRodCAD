# TE-002.1 — Security / Capability Surface

## WebView-facing IPC surface — unchanged from TE-002

TE-002.1 adds exactly two new `#[tauri::command]`s (`persistent_preview`, `persistent_shutdown`)
alongside the existing `request_preview`. All three follow the same pattern: they are
app-registered commands, callable by the WebView with only `core:default` capability — no shell,
process, or filesystem permission is ever granted to the WebView itself. The frontend's only
interaction with any of this is `invoke("persistent_preview")` / `invoke("persistent_shutdown")` /
`invoke("request_preview")`; it never touches `@tauri-apps/plugin-shell` or any process API
directly (`experiments/te002-tauri/frontend/src/sidecar.js`). This is the exact same
"process control belongs in Rust, never the WebView" boundary TE-002 established and TE-002.1 was
required to preserve — confirmed preserved by inspection of `capabilities/` (unchanged) and of
`sidecar.js` (no new imports beyond `@tauri-apps/api/core`).

## New surface introduced

- **A long-lived child process** instead of a fresh one per request. This is a real, if narrow,
  additional consideration: a persistent process has a longer window during which it could be
  targeted (e.g. via its stdin/stdout pipes) than a process that exits within ~150 ms of doing its
  one job. Mitigated the same way TE-002's one-shot process already was — the pipes are private to
  the parent process (not exposed to the WebView, not a listening network socket, no IPC
  mechanism other than the same stdin/stdout pair Rust already owned in TE-002), so this doesn't
  expand the actual attack surface beyond "the sidecar process runs for longer."
- **Shared mutable app state** (`PersistentEngineState`, a `Mutex<Option<PersistentEngine>>`).
  Standard Tauri managed-state pattern; access is serialized through the mutex, so no new
  concurrency-correctness risk beyond what any `tokio::sync::Mutex`-guarded state already carries.

## CSP — unchanged

`tauri.conf.json`'s `app.security.csp` is untouched from TE-002:
`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;
connect-src 'self' ipc: http://ipc.localhost`. No `dangerousRemoteDomainIpcAccess`-style broad
grant anywhere.

## Gatekeeper / code signing

The built test `.app` is unsigned (no Apple Developer ID involved in this evaluation, per the
mandate's explicit exclusion of any signing/notarization subproject). Launching it on a
Gatekeeper-enforcing macOS system requires the standard one-time "right-click → Open" override (or
an equivalent `xattr -d com.apple.quarantine` for automated/CI use) — see `HUMAN-VALIDATION.md`
for the exact instructions given to the human tester. No permanent Gatekeeper/SIP bypass was
configured or recommended anywhere in this evaluation.

## Not evaluated (out of scope for this TE)

Sandboxing/entitlements hardening, code signing, notarization, auto-update security, and any
threat model beyond "does the existing TE-002 IPC boundary still hold" — none of these were in
scope for a runtime-strategy comparison and none were touched.
