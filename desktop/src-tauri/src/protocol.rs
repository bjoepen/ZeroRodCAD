//! zerorod-sidecar/v1 request/response envelope — adopted stable from
//! docs/research/TE-002-Tauri-ThreeJS/Sidecar-Contract.md /
//! experiments/te002-tauri/src-tauri/src/sidecar.rs (TE-002/TE-002.1). No
//! protocol reinvention for Build 022 M2, per ADR-022-001.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;
use serde_json::Value;

pub const SIDECAR_SCHEMA: &str = "zerorod-sidecar/v1";

#[derive(Debug, Serialize, Clone, PartialEq)]
pub struct EngineError {
    pub code: String,
    pub message: String,
    /// Optional structured context (e.g. `field`/`expected`/`actual` for a
    /// zerorod-parameters/v1 validation failure) forwarded verbatim from the
    /// sidecar's `error.details` — Rust does not interpret it, only relays
    /// it (Build 023 M1, docs/contracts/ZEROROD-PARAMETERS-V1.md).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<Value>,
}

impl EngineError {
    pub fn new(code: &str, message: impl Into<String>) -> Self {
        Self {
            code: code.to_string(),
            message: message.into(),
            details: None,
        }
    }
}

/// Monotonic tie-breaker: some systems' `SystemTime` clock resolution is
/// coarser than a nanosecond, so two calls in quick succession can
/// otherwise produce identical timestamps.
static REQUEST_COUNTER: AtomicU64 = AtomicU64::new(0);

pub fn new_request_id() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let sequence = REQUEST_COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("req-{nanos}-{sequence}")
}

/// Builds the exact JSON line to write to the sidecar's stdin (includes the
/// trailing newline `sys.stdin.readline()` needs on the Python side).
///
/// `parameters` is forwarded verbatim — Rust does not interpret its shape
/// (e.g. a zerorod-parameters/v1 envelope for the `preview` command); it
/// only needs to serialize/deserialize the IPC boundary (Build 023 M1,
/// docs/contracts/ZEROROD-PARAMETERS-V1.md §21). Callers that don't need
/// parameters pass `serde_json::json!({})`, preserving the exact Build 022
/// wire shape.
pub fn build_request_line(command: &str, request_id: &str, parameters: &Value) -> String {
    serde_json::json!({
        "schema": SIDECAR_SCHEMA,
        "request_id": request_id,
        "command": command,
        "parameters": parameters,
    })
    .to_string()
        + "\n"
}

/// Parses one raw sidecar stdout line into the response `result` value, or a
/// structured `EngineError` — pure and independently testable.
pub fn parse_response(line: &str, expected_request_id: &str) -> Result<Value, EngineError> {
    let response: Value = serde_json::from_str(line).map_err(|e| {
        EngineError::new(
            "invalid_json",
            format!("sidecar stdout line was not valid JSON: {e}"),
        )
    })?;

    if response.get("schema").and_then(Value::as_str) != Some(SIDECAR_SCHEMA) {
        return Err(EngineError::new(
            "invalid_schema",
            format!("unexpected response schema: {:?}", response.get("schema")),
        ));
    }
    if response.get("request_id").and_then(Value::as_str) != Some(expected_request_id) {
        return Err(EngineError::new(
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
        let details = error.and_then(|e| e.get("details")).cloned();
        return Err(EngineError {
            code,
            message,
            details,
        });
    }

    response.get("result").cloned().ok_or_else(|| {
        EngineError::new(
            "missing_result",
            "ok response is missing the 'result' field",
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ok_line(request_id: &str, result: &str) -> String {
        format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"{request_id}","ok":true,"result":{result}}}"#
        )
    }

    #[test]
    fn build_request_line_has_expected_shape_and_trailing_newline() {
        let line = build_request_line("ping", "rid-1", &serde_json::json!({}));
        assert!(line.ends_with('\n'));
        let value: Value = serde_json::from_str(line.trim_end()).unwrap();
        assert_eq!(value["schema"], SIDECAR_SCHEMA);
        assert_eq!(value["command"], "ping");
        assert_eq!(value["request_id"], "rid-1");
        assert_eq!(value["parameters"], serde_json::json!({}));
    }

    #[test]
    fn build_request_line_forwards_non_empty_parameters_verbatim() {
        let parameters = serde_json::json!({
            "schema": "zerorod-parameters/v1",
            "values": {"body_width": 60.0},
        });
        let line = build_request_line("preview", "rid-1", &parameters);
        let value: Value = serde_json::from_str(line.trim_end()).unwrap();
        assert_eq!(value["parameters"], parameters);
    }

    #[test]
    fn build_request_line_forwards_export_combined_shape_verbatim() {
        // Build 024 M1: commands.rs's engine_export wraps the caller's
        // parameters and output_directory into this exact combined object —
        // proving the wire shape independent of a running sidecar/app.
        let parameters = serde_json::json!({
            "parameters": {
                "schema": "zerorod-parameters/v1",
                "values": {"body_width": 60.0},
            },
            "output_directory": "/tmp/some/chosen/dir",
        });
        let line = build_request_line("export", "rid-1", &parameters);
        let value: Value = serde_json::from_str(line.trim_end()).unwrap();
        assert_eq!(value["command"], "export");
        assert_eq!(value["parameters"], parameters);
    }

    #[test]
    fn parse_response_surfaces_export_result_shape() {
        let line = format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":true,"result":{{"output_directory":"/tmp/out","files":[{{"role":"body_stl","filename":"a.stl","path":"/tmp/out/a.stl"}}]}}}}"#
        );
        let result = parse_response(&line, "rid-1").unwrap();
        assert_eq!(result["output_directory"], "/tmp/out");
        assert_eq!(result["files"][0]["role"], "body_stl");
    }

    #[test]
    fn parse_response_surfaces_export_specific_error_codes() {
        let line = format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":false,"error":{{"code":"export_permission_denied","message":"denied"}}}}"#
        );
        let err = parse_response(&line, "rid-1").unwrap_err();
        assert_eq!(err.code, "export_permission_denied");
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
        let result = parse_response(&ok_line("rid-1", r#"{"status":"ok"}"#), "rid-1").unwrap();
        assert_eq!(result["status"], "ok");
    }

    #[test]
    fn parse_response_rejects_invalid_json() {
        let err = parse_response("not json", "rid-1").unwrap_err();
        assert_eq!(err.code, "invalid_json");
    }

    #[test]
    fn parse_response_rejects_wrong_schema() {
        let line = r#"{"schema":"wrong","request_id":"rid-1","ok":true,"result":{}}"#;
        let err = parse_response(line, "rid-1").unwrap_err();
        assert_eq!(err.code, "invalid_schema");
    }

    #[test]
    fn parse_response_rejects_request_id_mismatch() {
        let err = parse_response(&ok_line("other-id", "{}"), "rid-1").unwrap_err();
        assert_eq!(err.code, "request_id_mismatch");
    }

    #[test]
    fn parse_response_surfaces_sidecar_error_response() {
        let line = format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":false,"error":{{"code":"unknown_command","message":"nope"}}}}"#
        );
        let err = parse_response(&line, "rid-1").unwrap_err();
        assert_eq!(err.code, "unknown_command");
        assert_eq!(err.message, "nope");
        assert_eq!(err.details, None);
    }

    #[test]
    fn parse_response_surfaces_structured_error_details() {
        let line = format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":false,"error":{{"code":"invalid_parameter_type","message":"nope","details":{{"field":"body_width"}}}}}}"#
        );
        let err = parse_response(&line, "rid-1").unwrap_err();
        assert_eq!(err.code, "invalid_parameter_type");
        assert_eq!(
            err.details,
            Some(serde_json::json!({"field": "body_width"}))
        );
    }

    #[test]
    fn parse_response_rejects_ok_without_result() {
        let line = format!(r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":true}}"#);
        let err = parse_response(&line, "rid-1").unwrap_err();
        assert_eq!(err.code, "missing_result");
    }

    #[test]
    fn parse_response_rejects_malformed_error_object_with_defaults() {
        let line = format!(
            r#"{{"schema":"{SIDECAR_SCHEMA}","request_id":"rid-1","ok":false,"error":{{}}}}"#
        );
        let err = parse_response(&line, "rid-1").unwrap_err();
        assert_eq!(err.code, "unknown_error");
    }
}
