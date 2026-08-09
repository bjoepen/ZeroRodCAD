//! zerorod-mesh/v1 client-side validation — adopted stable from
//! docs/research/TE-002-Tauri-ThreeJS/Mesh-Contract.md /
//! tools/poc/tauri/sidecar/mesh_contract.py's `validate_mesh_contract`. M2
//! validates and summarizes the payload only (proves the end-to-end engine
//! data path); M3 is the actual Three.js consumer that renders it.

use serde::Serialize;
use serde_json::Value;

pub const MESH_SCHEMA: &str = "zerorod-mesh/v1";

#[derive(Debug, Serialize, Clone, PartialEq)]
pub struct MeshSummary {
    pub schema: String,
    pub mesh_count: usize,
    pub total_vertices: usize,
    pub total_triangles: usize,
    pub line_count: usize,
    pub bounds: Value,
}

fn is_finite_number(value: &Value) -> bool {
    value.as_f64().map(f64::is_finite).unwrap_or(false)
}

fn validate_bounds(payload: &Value, problems: &mut Vec<String>) {
    let bounds = payload.get("bounds");
    let has_both = bounds
        .map(|b| b.get("min").is_some() && b.get("max").is_some())
        .unwrap_or(false);
    if !has_both {
        problems.push("bounds must have 'min' and 'max'".to_string());
        return;
    }
    let bounds = bounds.unwrap();
    for key in ["min", "max"] {
        let valid = bounds
            .get(key)
            .and_then(Value::as_array)
            .map(|a| a.len() == 3 && a.iter().all(is_finite_number))
            .unwrap_or(false);
        if !valid {
            problems.push(format!("bounds.{key} must be [x, y, z] finite numbers"));
        }
    }
}

fn validate_mesh(mesh: &Value, problems: &mut Vec<String>) -> (usize, usize) {
    let name = mesh
        .get("name")
        .and_then(Value::as_str)
        .unwrap_or("<unnamed>");
    let positions = mesh.get("positions").and_then(Value::as_array);

    let vertex_count = match positions {
        None => {
            problems.push(format!("mesh '{name}': positions must be non-empty"));
            0
        }
        Some(p) if p.is_empty() => {
            problems.push(format!("mesh '{name}': positions must be non-empty"));
            0
        }
        Some(p) => {
            if p.len() % 3 != 0 {
                problems.push(format!(
                    "mesh '{name}': positions length {} not a multiple of 3",
                    p.len()
                ));
            }
            if p.iter().any(|v| !is_finite_number(v)) {
                problems.push(format!(
                    "mesh '{name}': positions contain NaN/Inf/non-numeric values"
                ));
            }
            p.len() / 3
        }
    };

    let indices = mesh.get("indices").and_then(Value::as_array);
    let triangle_count = match indices {
        None => {
            problems.push(format!("mesh '{name}': indices must be non-empty"));
            0
        }
        Some(i) if i.is_empty() => {
            problems.push(format!("mesh '{name}': indices must be non-empty"));
            0
        }
        Some(i) => {
            if i.len() % 3 != 0 {
                problems.push(format!(
                    "mesh '{name}': indices length {} not a multiple of 3",
                    i.len()
                ));
            }
            let out_of_range = i.iter().any(|v| {
                let value = v.as_i64();
                !value.is_some_and(|x| x >= 0 && (x as usize) < vertex_count)
            });
            if out_of_range {
                problems.push(format!(
                    "mesh '{name}': index out of range [0, {vertex_count})"
                ));
            }
            i.len() / 3
        }
    };

    (vertex_count, triangle_count)
}

/// Mirrors `zerorod_sidecar.mesh_contract.validate_mesh_contract` (same
/// checks: schema, non-empty meshes, positions/indices shape and range, no
/// NaN/Infinity, well-formed bounds), plus a summary an invoking command can
/// return to the frontend without shipping the full (potentially large)
/// geometry arrays over IPC before M3 actually needs them.
pub fn validate_and_summarize(payload: &Value) -> Result<MeshSummary, Vec<String>> {
    let mut problems = Vec::new();

    let schema = payload.get("schema").and_then(Value::as_str);
    if schema != Some(MESH_SCHEMA) {
        problems.push(format!("schema must be '{MESH_SCHEMA}', got {schema:?}"));
    }

    let meshes = payload.get("meshes").and_then(Value::as_array);
    let mesh_count = meshes.map(Vec::len).unwrap_or(0);
    let mut total_vertices = 0usize;
    let mut total_triangles = 0usize;

    match meshes.filter(|list| !list.is_empty()) {
        None => problems.push("meshes must be a non-empty list".to_string()),
        Some(list) => {
            for mesh in list {
                let (vertices, triangles) = validate_mesh(mesh, &mut problems);
                total_vertices += vertices;
                total_triangles += triangles;
            }
        }
    }

    let line_count = payload
        .get("lines")
        .and_then(Value::as_array)
        .map(Vec::len)
        .unwrap_or(0);

    validate_bounds(payload, &mut problems);

    if !problems.is_empty() {
        return Err(problems);
    }

    Ok(MeshSummary {
        schema: MESH_SCHEMA.to_string(),
        mesh_count,
        total_vertices,
        total_triangles,
        line_count,
        bounds: payload.get("bounds").cloned().unwrap_or(Value::Null),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn valid_payload() -> Value {
        json!({
            "schema": MESH_SCHEMA,
            "meshes": [
                {"name": "body", "positions": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0], "indices": [0, 1, 2]}
            ],
            "lines": [{"name": "strings", "positions": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]}],
            "bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
        })
    }

    #[test]
    fn accepts_a_well_formed_payload_and_summarizes_it() {
        let summary = validate_and_summarize(&valid_payload()).unwrap();
        assert_eq!(summary.mesh_count, 1);
        assert_eq!(summary.total_vertices, 3);
        assert_eq!(summary.total_triangles, 1);
        assert_eq!(summary.line_count, 1);
    }

    #[test]
    fn rejects_wrong_schema() {
        let mut payload = valid_payload();
        payload["schema"] = json!("wrong");
        let problems = validate_and_summarize(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("schema must be")));
    }

    #[test]
    fn rejects_empty_meshes() {
        let mut payload = valid_payload();
        payload["meshes"] = json!([]);
        let problems = validate_and_summarize(&payload).unwrap_err();
        assert!(problems
            .iter()
            .any(|p| p.contains("meshes must be a non-empty list")));
    }

    #[test]
    fn rejects_positions_not_a_multiple_of_three() {
        let mut payload = valid_payload();
        payload["meshes"][0]["positions"] = json!([0.0, 0.0]);
        let problems = validate_and_summarize(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("not a multiple of 3")));
    }

    #[test]
    fn rejects_index_out_of_range() {
        let mut payload = valid_payload();
        payload["meshes"][0]["indices"] = json!([0, 1, 99]);
        let problems = validate_and_summarize(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("index out of range")));
    }

    #[test]
    fn rejects_nan_in_positions() {
        let mut payload = valid_payload();
        payload["meshes"][0]["positions"] =
            json!([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, f64::NAN, 1.0, 0.0]);
        let problems = validate_and_summarize(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("NaN/Inf")));
    }

    #[test]
    fn rejects_missing_bounds() {
        let mut payload = valid_payload();
        payload.as_object_mut().unwrap().remove("bounds");
        let problems = validate_and_summarize(&payload).unwrap_err();
        assert!(problems.iter().any(|p| p.contains("bounds must have")));
    }
}
