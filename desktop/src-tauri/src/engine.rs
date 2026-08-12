//! Build 022 M2 — persistent sidecar engine manager.
//!
//! Owns the sidecar's process lifetime across multiple requests: spawn
//! (lazy — see docs/migration/BUILD-022-M2-SIDECAR-LIFECYCLE.md "Lazy vs.
//! eager start"), reuse, request/response with request_id validation,
//! timeout, crash detection + a single restart-once retry, and graceful
//! shutdown with a forced-kill fallback. Adapted from
//! experiments/te002-tauri/src-tauri/src/persistent.rs (TE-002.1 Variant C)
//! — persistent + onedir is the *only* productive runtime strategy
//! (ADR-022-001), so there is no one-shot sibling here.
//!
//! The WebView never sees any of this directly; `commands.rs` is the only
//! caller.

use std::time::Duration;

use serde::Serialize;
use serde_json::Value;
use tauri::async_runtime::Receiver;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tokio::sync::Mutex;

use crate::protocol::{build_request_line, new_request_id, parse_response, EngineError};

/// TE-002/TE-002.1's own value, reused without new evidence to change it
/// (ADR-022-001 "Performance baseline" carries the same reference forward).
pub const REQUEST_TIMEOUT_SECS: u64 = 30;
const SHUTDOWN_TIMEOUT_SECS: u64 = 5;

/// Resolved via Tauri's resource API against the onedir sidecar bundled as
/// a plain `resources` entry (not `externalBin`, which only supports
/// single-file sidecars — same reasoning as TE-002.1's `persistent.rs`).
const SIDECAR_RESOURCE_RELATIVE_PATH: &str = "zerorod-engine-onedir/zerorod-engine";

struct RunningEngine {
    child: CommandChild,
    receiver: Receiver<CommandEvent>,
    stdout_buffer: String,
    pid: u32,
}

/// Rust-side lifecycle state, independent of whether a request is currently
/// in flight — lets `engine_status` answer instantly without waiting on the
/// same lock a slow `preview` request might be holding.
#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum LifecycleState {
    Stopped,
    Running,
    Error,
}

#[derive(Debug, Clone, Serialize)]
pub struct EngineStatusInfo {
    pub state: LifecycleState,
    pub pid: Option<u32>,
    pub last_error: Option<EngineError>,
}

#[derive(Default)]
pub struct EngineState {
    engine: Mutex<Option<RunningEngine>>,
    last_error: Mutex<Option<EngineError>>,
}

fn extract_line(buffer: &mut String) -> Option<String> {
    let pos = buffer.find('\n')?;
    let line: String = buffer.drain(..=pos).collect();
    Some(line.trim_end().to_string())
}

impl RunningEngine {
    fn spawn(app: &AppHandle) -> Result<Self, EngineError> {
        let executable_path = app
            .path()
            .resolve(
                SIDECAR_RESOURCE_RELATIVE_PATH,
                tauri::path::BaseDirectory::Resource,
            )
            .map_err(|e| {
                EngineError::new(
                    "sidecar_missing",
                    format!("could not resolve onedir sidecar resource: {e}"),
                )
            })?;

        let command = app.shell().command(executable_path);
        let (receiver, child) = command.spawn().map_err(|e| {
            EngineError::new("spawn_failed", format!("failed to spawn sidecar: {e}"))
        })?;
        let pid = child.pid();

        Ok(Self {
            child,
            receiver,
            stdout_buffer: String::new(),
            pid,
        })
    }

    /// Sends one request, returns its `result` value. On timeout or a
    /// detected crash, the caller (`request`, below) decides whether to
    /// kill/restart — this method never restarts itself, keeping
    /// crash-detection and recovery-policy separate concerns.
    ///
    /// `parameters` is forwarded verbatim to the sidecar (Build 023 M1) —
    /// pass `serde_json::json!({})` for the parameterless Build 022 shape.
    async fn send(&mut self, command: &str, parameters: &Value) -> Result<Value, EngineError> {
        let request_id = new_request_id();
        let request_line = build_request_line(command, &request_id, parameters);

        self.child.write(request_line.as_bytes()).map_err(|e| {
            EngineError::new(
                "stdin_write_failed",
                format!("failed to write request: {e}"),
            )
        })?;

        let mut stderr_buf = String::new();
        let drain = async {
            loop {
                if let Some(line) = extract_line(&mut self.stdout_buffer) {
                    return Ok(line);
                }
                match self.receiver.recv().await {
                    Some(CommandEvent::Stdout(bytes)) => self
                        .stdout_buffer
                        .push_str(&String::from_utf8_lossy(&bytes)),
                    Some(CommandEvent::Stderr(bytes)) => {
                        stderr_buf.push_str(&String::from_utf8_lossy(&bytes))
                    }
                    Some(CommandEvent::Terminated(payload)) => {
                        return Err(format!(
                            "sidecar terminated unexpectedly (code {:?}) before responding: {}",
                            payload.code,
                            stderr_buf.trim()
                        ));
                    }
                    Some(CommandEvent::Error(err)) => {
                        return Err(format!("sidecar process error: {err}"))
                    }
                    Some(_) => continue,
                    None => return Err("sidecar event channel closed unexpectedly".to_string()),
                }
            }
        };

        let line =
            match tokio::time::timeout(Duration::from_secs(REQUEST_TIMEOUT_SECS), drain).await {
                Err(_elapsed) => {
                    return Err(EngineError::new(
                        "timeout",
                        format!("sidecar did not respond within {REQUEST_TIMEOUT_SECS}s"),
                    ));
                }
                Ok(Err(message)) => return Err(EngineError::new("sidecar_crashed", message)),
                Ok(Ok(line)) => line,
            };

        parse_response(&line, &request_id)
    }

    /// Best-effort graceful shutdown: send `shutdown`, wait briefly for the
    /// process to exit on its own, kill it if it doesn't.
    async fn shutdown(mut self) {
        let request_id = new_request_id();
        let line = build_request_line("shutdown", &request_id, &serde_json::json!({}));
        if self.child.write(line.as_bytes()).is_ok() {
            let wait = async {
                loop {
                    match self.receiver.recv().await {
                        Some(CommandEvent::Terminated(_)) | None => return,
                        Some(_) => continue,
                    }
                }
            };
            if tokio::time::timeout(Duration::from_secs(SHUTDOWN_TIMEOUT_SECS), wait)
                .await
                .is_ok()
            {
                return;
            }
        }
        let _ = self.child.kill();
    }

    fn kill(self) {
        let _ = self.child.kill();
    }
}

async fn ensure_started(
    guard: &mut tokio::sync::MutexGuard<'_, Option<RunningEngine>>,
    app: &AppHandle,
) -> Result<(), EngineError> {
    if guard.is_none() {
        **guard = Some(RunningEngine::spawn(app)?);
    }
    Ok(())
}

/// The one entry point `commands.rs` uses for every sidecar round trip
/// (`ping`, `status`, `preview`, `parameters_defaults`). Starts the sidecar
/// lazily on first use, reuses it afterward, and on a detected crash or
/// timeout kills the dead engine and retries exactly once against a freshly
/// spawned one — no unbounded retry loop, matching TE-002.1's "ein
/// expliziter Retry kann genügen" policy.
///
/// `parameters` is forwarded to the sidecar verbatim (Build 023 M1) — Rust
/// does not interpret it. Existing callers that don't need parameters pass
/// `serde_json::json!({})`, preserving the exact Build 022 wire shape.
pub async fn request(
    app: &AppHandle,
    state: &EngineState,
    command: &str,
    parameters: Value,
) -> Result<Value, EngineError> {
    let mut guard = state.engine.lock().await;

    if let Err(err) = ensure_started(&mut guard, app).await {
        *state.last_error.lock().await = Some(err.clone());
        return Err(err);
    }

    let result = guard.as_mut().unwrap().send(command, &parameters).await;
    let final_result = match result {
        Err(err) if err.code == "sidecar_crashed" || err.code == "timeout" => {
            if let Some(dead) = guard.take() {
                dead.kill();
            }
            *state.last_error.lock().await = Some(err.clone());
            if let Err(restart_err) = ensure_started(&mut guard, app).await {
                *state.last_error.lock().await = Some(restart_err.clone());
                return Err(restart_err);
            }
            guard.as_mut().unwrap().send(command, &parameters).await
        }
        other => other,
    };

    match &final_result {
        Ok(_) => *state.last_error.lock().await = None,
        Err(err) => *state.last_error.lock().await = Some(err.clone()),
    }
    final_result
}

/// Best-effort graceful shutdown, also invoked automatically on app exit
/// (see `lib.rs`'s `RunEvent::ExitRequested` handler).
pub async fn shutdown(state: &EngineState) {
    let mut guard = state.engine.lock().await;
    if let Some(engine) = guard.take() {
        engine.shutdown().await;
    }
}

/// Non-blocking: never awaits the same lock a slow request might hold. If
/// the lock is currently held, a request is in flight, which itself proves
/// the engine is running — reported as `Running` rather than blocking the
/// status query behind it.
pub fn status(state: &EngineState) -> EngineStatusInfo {
    match state.engine.try_lock() {
        Ok(guard) => match guard.as_ref() {
            Some(engine) => EngineStatusInfo {
                state: LifecycleState::Running,
                pid: Some(engine.pid),
                last_error: None,
            },
            None => {
                let last_error = state.last_error.try_lock().ok().and_then(|g| g.clone());
                EngineStatusInfo {
                    state: if last_error.is_some() {
                        LifecycleState::Error
                    } else {
                        LifecycleState::Stopped
                    },
                    pid: None,
                    last_error,
                }
            }
        },
        Err(_) => EngineStatusInfo {
            state: LifecycleState::Running,
            pid: None,
            last_error: None,
        },
    }
}

/// Non-command helper: forcibly kills any running engine without waiting
/// for a graceful shutdown round-trip — used from the app's exit handler,
/// where blocking on a full async round-trip is not available. No sidecar
/// process may outlive the app (TE-002.1 section 17); this is the fallback
/// for whatever `RunEvent::ExitRequested`'s best-effort async shutdown
/// attempt does not finish in time.
pub fn kill_if_running(app: &AppHandle) {
    let state = app.state::<EngineState>();
    let Ok(mut guard) = state.engine.try_lock() else {
        return;
    };
    if let Some(engine) = guard.take() {
        engine.kill();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extract_line_returns_none_on_incomplete_buffer() {
        let mut buffer = String::from("{\"schema\":\"zerorod-sidecar/v1\"");
        assert_eq!(extract_line(&mut buffer), None);
        assert!(buffer.starts_with("{\"schema\""));
    }

    #[test]
    fn extract_line_returns_first_complete_line_and_leaves_remainder() {
        let mut buffer = String::from("{\"a\":1}\n{\"b\":2}\n{\"c\":3");
        assert_eq!(extract_line(&mut buffer), Some(r#"{"a":1}"#.to_string()));
        assert_eq!(extract_line(&mut buffer), Some(r#"{"b":2}"#.to_string()));
        assert_eq!(extract_line(&mut buffer), None);
        assert_eq!(buffer, r#"{"c":3"#);
    }

    #[test]
    fn extract_line_handles_a_line_arriving_across_multiple_pushes() {
        let mut buffer = String::new();
        buffer.push_str("{\"schema\":\"zerorod-sidecar/v1\",");
        assert_eq!(extract_line(&mut buffer), None);
        buffer.push_str("\"ok\":true}\n");
        assert_eq!(
            extract_line(&mut buffer),
            Some(r#"{"schema":"zerorod-sidecar/v1","ok":true}"#.to_string())
        );
    }

    #[test]
    fn status_of_a_fresh_state_is_stopped_with_no_pid_and_no_error() {
        let state = EngineState::default();
        let info = status(&state);
        assert_eq!(info.state, LifecycleState::Stopped);
        assert_eq!(info.pid, None);
        assert!(info.last_error.is_none());
    }
}
