//! Build 024 M3 — structural validation of the sidecar's `export`/
//! `export_preflight` JSON results, mirroring `mesh.rs`'s
//! `validate_and_summarize` pattern for `zerorod-mesh/v1`: the sidecar is a
//! trusted local process, but nothing Rust-side previously checked the
//! *shape* of an export result before relaying it straight to the WebView
//! as a success value. A missing/wrong-typed field there would previously
//! have reached the frontend's `success` render path unchecked (§10/§23/§34
//! of the M3 mandate: a malformed result must never read as success). This
//! validates the same fixed, known role set `zerorodcad.export.
//! expected_output_filenames` always produces — it does not duplicate that
//! logic, only checks the wire shape already agreed by both sides.

use serde_json::Value;

const EXPECTED_ROLES: [&str; 3] = ["body_stl", "assembly_step", "report_markdown"];

fn non_empty_str(value: Option<&Value>) -> bool {
    value.and_then(Value::as_str).is_some_and(|s| !s.is_empty())
}

fn validate_role_filename_entries(
    entries: &Value,
    field_name: &str,
    require_all_expected_roles: bool,
    problems: &mut Vec<String>,
) {
    let Some(array) = entries.as_array() else {
        problems.push(format!("'{field_name}' must be an array"));
        return;
    };
    let mut seen_roles = Vec::new();
    for (index, entry) in array.iter().enumerate() {
        if !non_empty_str(entry.get("role")) {
            problems.push(format!("'{field_name}[{index}]' missing non-empty 'role'"));
            continue;
        }
        if !non_empty_str(entry.get("filename")) {
            problems.push(format!(
                "'{field_name}[{index}]' missing non-empty 'filename'"
            ));
        }
        let role = entry.get("role").and_then(Value::as_str).unwrap_or("");
        if !EXPECTED_ROLES.contains(&role) {
            problems.push(format!(
                "'{field_name}[{index}]' has unexpected role '{role}'"
            ));
        }
        seen_roles.push(role);
    }
    if require_all_expected_roles {
        for expected in EXPECTED_ROLES {
            if !seen_roles.contains(&expected) {
                problems.push(format!(
                    "'{field_name}' is missing expected role '{expected}'"
                ));
            }
        }
    }
}

/// Validates `engine_export`'s result: `output_directory` (non-empty
/// string) and `files` (array covering exactly the three expected roles,
/// each with non-empty `role`/`filename`/`path`). Does not re-check
/// `timing` — informational only, never used for a correctness decision.
pub fn validate_export_result(payload: &Value) -> Result<(), Vec<String>> {
    let mut problems = Vec::new();

    if !non_empty_str(payload.get("output_directory")) {
        problems.push("'output_directory' must be a non-empty string".to_string());
    }

    match payload.get("files") {
        Some(files) => {
            validate_role_filename_entries(files, "files", true, &mut problems);
            if let Some(array) = files.as_array() {
                for (index, entry) in array.iter().enumerate() {
                    if !non_empty_str(entry.get("path")) {
                        problems.push(format!("'files[{index}]' missing non-empty 'path'"));
                    }
                }
            }
        }
        None => problems.push("'files' is required".to_string()),
    }

    if problems.is_empty() {
        Ok(())
    } else {
        Err(problems)
    }
}

/// Validates `engine_export_preflight`'s result: `output_directory`,
/// `expected_files` (all three known roles), `conflicts` (a subset of the
/// same known roles), and `has_conflicts` consistent with whether
/// `conflicts` is actually non-empty — the last check catches a
/// wrong-shape/stale-flag response that unit tests alone might miss.
pub fn validate_export_preflight_result(payload: &Value) -> Result<(), Vec<String>> {
    let mut problems = Vec::new();

    if !non_empty_str(payload.get("output_directory")) {
        problems.push("'output_directory' must be a non-empty string".to_string());
    }

    match payload.get("expected_files") {
        Some(expected) => {
            validate_role_filename_entries(expected, "expected_files", true, &mut problems)
        }
        None => problems.push("'expected_files' is required".to_string()),
    }

    let conflicts_len = match payload.get("conflicts") {
        Some(conflicts) => {
            validate_role_filename_entries(conflicts, "conflicts", false, &mut problems);
            conflicts.as_array().map(Vec::len)
        }
        None => {
            problems.push("'conflicts' is required".to_string());
            None
        }
    };

    match (
        payload.get("has_conflicts").and_then(Value::as_bool),
        conflicts_len,
    ) {
        (Some(has_conflicts), Some(len)) if has_conflicts != (len > 0) => {
            problems.push("'has_conflicts' is inconsistent with 'conflicts'".to_string());
        }
        (None, _) => problems.push("'has_conflicts' must be a boolean".to_string()),
        _ => {}
    }

    if problems.is_empty() {
        Ok(())
    } else {
        Err(problems)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_export_result() -> Value {
        serde_json::json!({
            "output_directory": "/tmp/out",
            "files": [
                {"role": "body_stl", "filename": "a-body.stl", "path": "/tmp/out/a-body.stl"},
                {"role": "assembly_step", "filename": "a-assembly.step", "path": "/tmp/out/a-assembly.step"},
                {"role": "report_markdown", "filename": "a-report.md", "path": "/tmp/out/a-report.md"},
            ],
            "timing": {"export_seconds": 0.13},
        })
    }

    fn valid_preflight_result() -> Value {
        serde_json::json!({
            "output_directory": "/tmp/out",
            "expected_files": [
                {"role": "body_stl", "filename": "a-body.stl"},
                {"role": "assembly_step", "filename": "a-assembly.step"},
                {"role": "report_markdown", "filename": "a-report.md"},
            ],
            "conflicts": [],
            "has_conflicts": false,
        })
    }

    #[test]
    fn accepts_a_well_formed_export_result() {
        assert!(validate_export_result(&valid_export_result()).is_ok());
    }

    #[test]
    fn rejects_missing_output_directory() {
        let mut payload = valid_export_result();
        payload.as_object_mut().unwrap().remove("output_directory");
        let problems = validate_export_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("output_directory")));
    }

    #[test]
    fn rejects_missing_files_field() {
        let mut payload = valid_export_result();
        payload.as_object_mut().unwrap().remove("files");
        let problems = validate_export_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("'files' is required")));
    }

    #[test]
    fn rejects_a_result_missing_an_expected_role() {
        let mut payload = valid_export_result();
        let files = payload.get_mut("files").unwrap().as_array_mut().unwrap();
        files.retain(|f| f["role"] != "assembly_step");
        let problems = validate_export_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("assembly_step")));
    }

    #[test]
    fn rejects_an_unexpected_file_role() {
        let mut payload = valid_export_result();
        payload["files"][0]["role"] = Value::String("mystery_role".to_string());
        let problems = validate_export_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("mystery_role")));
    }

    #[test]
    fn rejects_a_file_entry_missing_path() {
        let mut payload = valid_export_result();
        payload["files"][0].as_object_mut().unwrap().remove("path");
        let problems = validate_export_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("path")));
    }

    #[test]
    fn rejects_files_as_wrong_type() {
        let mut payload = valid_export_result();
        payload["files"] = Value::String("not an array".to_string());
        let problems = validate_export_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("must be an array")));
    }

    #[test]
    fn accepts_a_well_formed_preflight_result() {
        assert!(validate_export_preflight_result(&valid_preflight_result()).is_ok());
    }

    #[test]
    fn accepts_a_preflight_result_with_real_conflicts() {
        let mut payload = valid_preflight_result();
        payload["conflicts"] = serde_json::json!([{"role": "body_stl", "filename": "a-body.stl"}]);
        payload["has_conflicts"] = Value::Bool(true);
        assert!(validate_export_preflight_result(&payload).is_ok());
    }

    #[test]
    fn rejects_has_conflicts_inconsistent_with_conflicts_array() {
        let mut payload = valid_preflight_result();
        payload["has_conflicts"] = Value::Bool(true); // conflicts is still []
        let problems = validate_export_preflight_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("inconsistent")));
    }

    #[test]
    fn rejects_preflight_result_missing_expected_files() {
        let mut payload = valid_preflight_result();
        payload.as_object_mut().unwrap().remove("expected_files");
        let problems = validate_export_preflight_result(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("expected_files")));
    }
}
