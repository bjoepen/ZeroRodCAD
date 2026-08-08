//! TE-002.1 Variant C — persistent sidecar engine manager (section 16).
//!
//! Owns the sidecar's process lifetime across multiple requests. The
//! WebView never sees this directly — it only calls the
//! `persistent_preview`/`persistent_shutdown` commands, same IPC boundary
//! as the one-shot `request_preview` (section 6: the architecture boundary
//! is unchanged, only what happens on the Rust side of it).

use std::time::Duration;

use serde_json::Value;
use tauri::async_runtime::Receiver;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tokio::sync::Mutex;

use crate::sidecar::{new_request_id, parse_response, PreviewError, SIDECAR_SCHEMA};

const REQUEST_TIMEOUT_SECS: u64 = 30;
const SHUTDOWN_TIMEOUT_SECS: u64 = 5;

struct PersistentEngine {
    child: CommandChild,
    receiver: Receiver<CommandEvent>,
    stdout_buffer: String,
}

/// Shared app state: `None` when no persistent sidecar is currently
/// running (not yet started, or cleaned up after a crash/shutdown).
#[derive(Default)]
pub struct PersistentEngineState(Mutex<Option<PersistentEngine>>);

/// Extracts one complete newline-terminated line from a growing byte
/// buffer, leaving any remainder for the next call — pure and unit-testable
/// in isolation from the real stdout channel/process (deliberately kept
/// simple rather than adding a mocked-Tauri-app test harness, section 41).
fn extract_line(buffer: &mut String) -> Option<String> {
    let pos = buffer.find('\n')?;
    let line: String = buffer.drain(..=pos).collect();
    Some(line.trim_end().to_string())
}

fn build_request_line(command: &str, request_id: &str) -> String {
    serde_json::json!({
        "schema": SIDECAR_SCHEMA,
        "request_id": request_id,
        "command": command,
        "parameters": {},
    })
    .to_string()
        + "\n"
}

impl PersistentEngine {
    /// TE-002.1's own measurements (Performance.md / Process-Lifecycle.md)
    /// showed the onefile `externalBin` sidecar used by the one-shot
    /// `request_preview` command has both a ~15-30s cold-start cost (self-
    /// extraction) and an unreliable-kill risk (its forked worker process
    /// can be orphaned by a plain SIGKILL on the bootloader PID). The
    /// persistent engine therefore spawns the onedir-packaged build instead
    /// — bundled as a plain `resources` entry (Tauri's `externalBin`
    /// mechanism only supports single-file sidecars, not a directory tree),
    /// resolved at runtime via the standard resource-path API and launched
    /// with `Shell::command()` (the same underlying Command/CommandChild
    /// types `sidecar()` returns, just not gated by the externalBin naming
    /// convention).
    fn spawn(app: &AppHandle) -> Result<Self, PreviewError> {
        let executable_path = app
            .path()
            .resolve(
                "zerorod-engine-onedir/zerorod-engine",
                tauri::path::BaseDirectory::Resource,
            )
            .map_err(|e| {
                PreviewError::new(
                    "sidecar_missing",
                    format!("could not resolve onedir sidecar resource: {e}"),
                )
            })?;

        let command = app.shell().command(executable_path).args(["--persistent"]);

        let (receiver, child) = command.spawn().map_err(|e| {
            PreviewError::new(
                "spawn_failed",
                format!("failed to spawn persistent sidecar: {e}"),
            )
        })?;

        Ok(Self {
            child,
            receiver,
            stdout_buffer: String::new(),
        })
    }

    /// Sends one request, returns its `result` value. On timeout the child
    /// is killed (section 18: no zombie left behind). On crash (the
    /// process terminates before responding) an error is returned so the
    /// caller can decide to restart — this function never restarts itself,
    /// keeping crash-detection and recovery-policy separate concerns.
    async fn request(&mut self, command: &str) -> Result<Value, PreviewError> {
        let request_id = new_request_id();
        let request_line = build_request_line(command, &request_id);

        self.child.write(request_line.as_bytes()).map_err(|e| {
            PreviewError::new(
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

        let line = match tokio::time::timeout(Duration::from_secs(REQUEST_TIMEOUT_SECS), drain)
            .await
        {
            // Note: does NOT kill self.child here — CommandChild::kill()
            // consumes its receiver, which isn't possible through &mut self.
            // The caller (persistent_preview) takes ownership of the whole
            // engine and kills it whenever "timeout"/"sidecar_crashed" is
            // returned, exactly like the crash-recovery path already does.
            Err(_elapsed) => {
                return Err(PreviewError::new(
                    "timeout",
                    format!("persistent sidecar did not respond within {REQUEST_TIMEOUT_SECS}s"),
                ));
            }
            Ok(Err(message)) => return Err(PreviewError::new("sidecar_crashed", message)),
            Ok(Ok(line)) => line,
        };

        parse_response(&line, &request_id)
    }

    /// Best-effort graceful shutdown: send `shutdown`, wait briefly for the
    /// process to exit on its own, kill it if it doesn't (section 17/18).
    async fn shutdown(mut self) {
        let request_id = new_request_id();
        let line = build_request_line("shutdown", &request_id);
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

async fn ensure_started<'a>(
    guard: &mut tokio::sync::MutexGuard<'a, Option<PersistentEngine>>,
    app: &AppHandle,
) -> Result<(), PreviewError> {
    if guard.is_none() {
        **guard = Some(PersistentEngine::spawn(app)?);
    }
    Ok(())
}

/// TE-002.1 Variant C command: the frontend calls this exactly like the
/// one-shot `request_preview` — it is unaware whether a fresh process or a
/// reused one served the request. On a detected crash *or* timeout, the
/// dead/hung engine is killed and removed, and a single restart+retry is
/// attempted (section 18: "Ein expliziter Retry kann für TE-002.1
/// genügen" — no complex supervisor).
#[tauri::command]
pub async fn persistent_preview(
    app: AppHandle,
    state: State<'_, PersistentEngineState>,
) -> Result<Value, PreviewError> {
    let mut guard = state.0.lock().await;
    ensure_started(&mut guard, &app).await?;

    let result = guard.as_mut().unwrap().request("preview").await;
    match result {
        Err(err) if err.code == "sidecar_crashed" || err.code == "timeout" => {
            // Take ownership so kill() (which consumes CommandChild) is
            // possible, then restart+retry exactly once.
            if let Some(dead) = guard.take() {
                dead.kill();
            }
            ensure_started(&mut guard, &app).await?;
            guard.as_mut().unwrap().request("preview").await
        }
        other => other,
    }
}

/// Explicit shutdown command (also invoked automatically on app exit — see
/// `lib.rs`'s `RunEvent::ExitRequested` handler, section 17).
#[tauri::command]
pub async fn persistent_shutdown(
    state: State<'_, PersistentEngineState>,
) -> Result<(), PreviewError> {
    let mut guard = state.0.lock().await;
    if let Some(engine) = guard.take() {
        engine.shutdown().await;
    }
    Ok(())
}

/// Non-command helper: forcibly kills any running persistent engine without
/// waiting for a graceful shutdown round-trip — used from the app's exit
/// handler where blocking on an async round-trip is not available.
pub fn kill_if_running(app: &AppHandle) {
    let state = app.state::<PersistentEngineState>();
    let mut lock_result = state.0.try_lock();
    if let Ok(guard) = lock_result.as_mut() {
        if let Some(engine) = guard.take() {
            engine.kill();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extract_line_returns_none_on_incomplete_buffer() {
        let mut buffer = String::from("{\"schema\":\"zerorod-sidecar/v1\"");
        assert_eq!(extract_line(&mut buffer), None);
        // buffer must be untouched, so the next chunk can still be appended
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
    fn build_request_line_persistent_has_expected_shape_and_trailing_newline() {
        let line = build_request_line("preview", "rid-1");
        assert!(line.ends_with('\n'));
        let value: Value = serde_json::from_str(line.trim_end()).unwrap();
        assert_eq!(value["schema"], SIDECAR_SCHEMA);
        assert_eq!(value["command"], "preview");
        assert_eq!(value["request_id"], "rid-1");
    }

    #[test]
    fn build_request_line_supports_shutdown_command() {
        let line = build_request_line("shutdown", "rid-2");
        let value: Value = serde_json::from_str(line.trim_end()).unwrap();
        assert_eq!(value["command"], "shutdown");
    }
}
