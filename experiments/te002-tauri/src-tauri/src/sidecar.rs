//! TE-002 sidecar bridge (sections 17-18). All process control and protocol
//! handling lives here in Rust — the frontend only ever calls the
//! `request_preview` Tauri command, never spawns a process itself.

use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::Serialize;
use serde_json::Value;
use tauri::AppHandle;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

pub const SIDECAR_SCHEMA: &str = "zerorod-sidecar/v1";
pub const SIDECAR_NAME: &str = "zerorod-engine";
pub const SIDECAR_TIMEOUT_SECS: u64 = 30;

#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct PreviewError {
    pub code: String,
    pub message: String,
}

impl PreviewError {
    fn new(code: &str, message: impl Into<String>) -> Self {
        Self {
            code: code.to_string(),
            message: message.into(),
        }
    }
}

/// Builds a request_id and the exact JSON line to write to the sidecar's
/// stdin (includes the trailing newline the sidecar's `readline()` needs).
pub fn build_request_line(request_id: &str) -> String {
    serde_json::json!({
        "schema": SIDECAR_SCHEMA,
        "request_id": request_id,
        "command": "preview",
        "parameters": {},
    })
    .to_string()
        + "\n"
}

pub fn new_request_id() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("req-{nanos}")
}

/// Parses raw sidecar stdout into the mesh-contract `result` value, or a
/// structured `PreviewError` — pure and independently testable (section 30:
/// "Sidecar response parsing, error response, malformed JSON").
pub fn parse_response(stdout: &str, expected_request_id: &str) -> Result<Value, PreviewError> {
    let lines: Vec<&str> = stdout.lines().filter(|l| !l.trim().is_empty()).collect();
    if lines.len() != 1 {
        return Err(PreviewError::new(
            "malformed_output",
            format!(
                "expected exactly one JSON line on stdout, got {}",
                lines.len()
            ),
        ));
    }

    let response: Value = serde_json::from_str(lines[0]).map_err(|e| {
        PreviewError::new(
            "invalid_json",
            format!("sidecar stdout was not valid JSON: {e}"),
        )
    })?;

    if response.get("schema").and_then(Value::as_str) != Some(SIDECAR_SCHEMA) {
        return Err(PreviewError::new(
            "invalid_schema",
            format!("unexpected response schema: {:?}", response.get("schema")),
        ));
    }
    if response.get("request_id").and_then(Value::as_str) != Some(expected_request_id) {
        return Err(PreviewError::new(
            "request_id_mismatch",
            format!(
                "response request_id {:?} does not match request {expected_request_id}",
                response.get("request_id")
            ),
        ));
    }

    let ok = response.get("ok").and_then(Value::as_bool).unwrap_or(false);
    if !ok {
        let error = response.get("error");
        let code = error
            .and_then(|e| e.get("code"))
            .and_then(Value::as_str)
            .unwrap_or("unknown_error")
            .to_string();
        let message = error
            .and_then(|e| e.get("message"))
            .and_then(Value::as_str)
            .unwrap_or("sidecar reported an error with no message")
            .to_string();
        return Err(PreviewError { code, message });
    }

    response.get("result").cloned().ok_or_else(|| {
        PreviewError::new(
            "missing_result",
            "ok response is missing the 'result' field",
        )
    })
}

/// Spawns the sidecar, writes the request, waits (with a timeout) for it to
/// exit, and returns the parsed mesh-contract result. On timeout the child
/// process is killed — no zombie sidecar is left behind (section 18).
#[tauri::command]
pub async fn request_preview(app: AppHandle) -> Result<Value, PreviewError> {
    let request_id = new_request_id();
    let request_line = build_request_line(&request_id);

    let sidecar_command = app.shell().sidecar(SIDECAR_NAME).map_err(|e| {
        PreviewError::new(
            "sidecar_missing",
            format!("could not resolve sidecar binary: {e}"),
        )
    })?;

    let (mut receiver, mut child) = sidecar_command
        .spawn()
        .map_err(|e| PreviewError::new("spawn_failed", format!("failed to spawn sidecar: {e}")))?;

    child.write(request_line.as_bytes()).map_err(|e| {
        PreviewError::new(
            "stdin_write_failed",
            format!("failed to write request: {e}"),
        )
    })?;

    let mut stdout_buf = String::new();
    let mut stderr_buf = String::new();
    let mut exit_code: Option<i32> = None;

    let drain = async {
        while let Some(event) = receiver.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    stdout_buf.push_str(&String::from_utf8_lossy(&bytes))
                }
                CommandEvent::Stderr(bytes) => {
                    stderr_buf.push_str(&String::from_utf8_lossy(&bytes))
                }
                CommandEvent::Terminated(payload) => {
                    exit_code = payload.code;
                    break;
                }
                CommandEvent::Error(err) => return Err(err),
                _ => {}
            }
        }
        Ok(())
    };

    match tokio::time::timeout(Duration::from_secs(SIDECAR_TIMEOUT_SECS), drain).await {
        Err(_elapsed) => {
            let _ = child.kill();
            return Err(PreviewError::new(
                "timeout",
                format!("sidecar did not respond within {SIDECAR_TIMEOUT_SECS}s"),
            ));
        }
        Ok(Err(process_error)) => {
            return Err(PreviewError::new(
                "process_error",
                format!("sidecar process error: {process_error}"),
            ));
        }
        Ok(Ok(())) => {}
    }

    if exit_code != Some(0) {
        return Err(PreviewError::new(
            "nonzero_exit",
            format!(
                "sidecar exited with code {exit_code:?}: {}",
                stderr_buf.trim()
            ),
        ));
    }

    parse_response(&stdout_buf, &request_id)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ok_stdout(request_id: &str) -> String {
        format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"{request_id}","ok":true,"result":{{"schema":"zerorod-mesh/v1","meshes":[]}}}}"#
        ) + "\n"
    }

    #[test]
    fn build_request_line_has_expected_shape() {
        let line = build_request_line("rid-1");
        let value: Value = serde_json::from_str(line.trim_end()).unwrap();
        assert_eq!(value["schema"], SIDECAR_SCHEMA);
        assert_eq!(value["request_id"], "rid-1");
        assert_eq!(value["command"], "preview");
        assert!(line.ends_with('\n'));
    }

    #[test]
    fn new_request_id_is_non_empty_and_varies() {
        let a = new_request_id();
        let b = new_request_id();
        assert!(!a.is_empty());
        assert_ne!(a, b, "two calls in quick succession should still differ");
    }

    #[test]
    fn parse_response_accepts_valid_ok_response() {
        let result = parse_response(&ok_stdout("rid-1"), "rid-1").unwrap();
        assert_eq!(result["schema"], "zerorod-mesh/v1");
    }

    #[test]
    fn parse_response_rejects_empty_stdout() {
        let err = parse_response("", "rid-1").unwrap_err();
        assert_eq!(err.code, "malformed_output");
    }

    #[test]
    fn parse_response_rejects_multiple_lines() {
        let stdout = format!("{}{}", ok_stdout("rid-1"), ok_stdout("rid-1"));
        let err = parse_response(&stdout, "rid-1").unwrap_err();
        assert_eq!(err.code, "malformed_output");
    }

    #[test]
    fn parse_response_rejects_invalid_json() {
        let err = parse_response("not json\n", "rid-1").unwrap_err();
        assert_eq!(err.code, "invalid_json");
    }

    #[test]
    fn parse_response_rejects_wrong_schema() {
        let stdout =
            r#"{"schema":"wrong","request_id":"rid-1","ok":true,"result":{}}"#.to_string() + "\n";
        let err = parse_response(&stdout, "rid-1").unwrap_err();
        assert_eq!(err.code, "invalid_schema");
    }

    #[test]
    fn parse_response_rejects_request_id_mismatch() {
        let err = parse_response(&ok_stdout("other-id"), "rid-1").unwrap_err();
        assert_eq!(err.code, "request_id_mismatch");
    }

    #[test]
    fn parse_response_surfaces_sidecar_error_response() {
        let stdout = format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":false,"error":{{"code":"unknown_command","message":"nope"}}}}"#
        ) + "\n";
        let err = parse_response(&stdout, "rid-1").unwrap_err();
        assert_eq!(err.code, "unknown_command");
        assert_eq!(err.message, "nope");
    }

    #[test]
    fn parse_response_rejects_ok_without_result() {
        let stdout =
            format!(r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":true}}"#) + "\n";
        let err = parse_response(&stdout, "rid-1").unwrap_err();
        assert_eq!(err.code, "missing_result");
    }
}
