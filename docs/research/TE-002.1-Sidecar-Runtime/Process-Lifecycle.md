# TE-002.1 — Process Lifecycle

The mandate treats process cleanup as non-negotiable: after the app ends, no `zerorod-engine`
process may remain, under any of the following triggers — normal close, window close, idle,
mid-request, timeout, crash, or app shutdown. This is the section of TE-002.1 that ended up
producing the decisive finding for the final recommendation.

## Rust-side engine manager (`experiments/te002-tauri/src-tauri/src/persistent.rs`)

`PersistentEngineState` holds at most one `PersistentEngine` (a `CommandChild` + response
receiver + line-buffer) behind a `tokio::sync::Mutex`, shared app state. Lifecycle:

- **Start**: lazy — `persistent_preview` starts the engine on first use (`ensure_started`), not
  at app launch. No process exists until the first request.
- **Request timeout**: 30 s (`REQUEST_TIMEOUT_SECS`). On timeout, the caller takes ownership of
  the engine (`guard.take()`) and kills it, then starts a fresh one and retries the request
  exactly once — "ein expliziter Retry kann genügen," no supervisor beyond that.
- **Crash detection**: a `CommandEvent::Terminated` arriving before a response counts as a crash;
  handled identically to a timeout (kill, restart, retry once).
- **Explicit shutdown**: `persistent_shutdown` sends a `shutdown` command, waits up to 5 s for the
  process to exit on its own, force-kills only if it doesn't.
- **App exit**: `lib.rs`'s `RunEvent::ExitRequested` handler calls `kill_if_running`, a
  non-async best-effort kill (can't block on an async round trip from inside the exit-event
  callback), so an in-flight or idle engine is never simply abandoned when the window closes.

## The finding: onefile kill is not reliable, onedir kill is

`tauri-plugin-shell` 2.3.5's `CommandChild::kill()` is a single-PID `SIGKILL`
(`shared_child::SharedChild::kill()` → plain `std::process::Child::kill()`) — verified by reading
the crate source directly: no `setsid`/`process_group`/`killpg` anywhere in it. A PyInstaller
**onefile** executable is a bootloader process that forks/execs a separate worker child that does
all the real work. Killing only the bootloader PID does not terminate that forked worker — it
becomes orphaned, keeps running, and keeps the shared stdout pipe open (any reader still waiting
on that pipe hangs indefinitely).

Three direct tests, `build/reports/te0021-sidecar-runtime/process-cleanup-findings.json`:

| Test | Result |
|---|---|
| Kill onefile's top-level (bootloader) PID | Forked worker child confirmed present before kill; reader hung 5s+ waiting on the pipe; worker left running as an orphan after the kill |
| Kill the onefile worker child directly | Parent bootloader also exits cleanly (normal wait-for-child propagation); no leftover |
| Kill onedir's top-level PID | No forked child (onedir doesn't fork); reader got EOF within 5s; no leftover process |

**Root cause, in one sentence**: any Rust-triggered forced kill of a onefile sidecar (timeout,
crash-recovery restart, or app-exit cleanup) risks leaving an orphaned worker process behind,
because `CommandChild::kill()` only ever signals the top-level PID and onefile's real work happens
in an unrelated forked child. This risk is structural to onefile packaging, not to the persistent
transport mode specifically — though persistent mode is more exposed to it in practice, since a
long-lived process has more opportunities to need a forced kill (an idle timeout, a crash mid-way
through many requests) than a one-shot process that normally exits on its own within a second.
onedir has zero exposure to this failure mode, by construction (single process, nothing to
orphan).

## Confirmed clean at every trigger, for the chosen variant (D)

- Normal `shutdown` request → process exits with code 0, no leftover (`shutdown_response_ok: true`
  in both `variant-c-persistent-onefile.json` and `variant-d-persistent-onedir.json`).
- Forced kill (top-level PID) → clean exit, no leftover (`onedir_top_level_kill_test` above).
- App-exit handler (`kill_if_running`) → exercised via the real built `.app` bundle: launched,
  main process confirmed running, then killed; no `zerorod-engine` process left behind
  afterward (`ps aux` empty for both the app's own process and any sidecar).

## Not independently re-tested

Idle-timeout cleanup (no idle timer exists in this PoC — the engine stays alive until an explicit
shutdown, an app exit, or a request failure; a real product would likely want one, not built here
since it wasn't required for the variant comparison itself) and a crash triggered by something
other than a forced kill (e.g. an actual Python-level unhandled exception crashing the worker) —
the crash-recovery *code path* is covered by the timeout/`Terminated`-event handling above and by
existing Rust unit/integration tests, but a live, spontaneous crash was not separately staged.
