//! Tauri commands exposed to the WebView. `app_info` (M1) proves the IPC
//! bridge; the `engine_*` commands (M2/M3) are the only way the frontend
//! can reach the Python sidecar — all process control stays in `engine.rs`.

use serde::Serialize;
use serde_json::Value;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::{DialogExt, FilePath};

use crate::engine::{self, EngineState, EngineStatusInfo};
use crate::mesh;
use crate::protocol::EngineError;

#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct AppInfo {
    pub name: String,
    pub version: String,
    pub build: String,
    pub milestone: String,
}

#[tauri::command]
pub fn app_info() -> AppInfo {
    AppInfo {
        name: "ZeroRodCAD Desktop".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        build: "022".to_string(),
        milestone: "M3".to_string(),
    }
}

/// Rust-side lifecycle status — instant, does not itself talk to the
/// sidecar (see `engine::status`'s non-blocking `try_lock`).
#[tauri::command]
pub fn engine_status(state: State<'_, EngineState>) -> EngineStatusInfo {
    engine::status(&state)
}

/// Round-trips the sidecar's `ping` command — proves the process is not
/// just spawned but actually answering requests. Starts the sidecar lazily
/// on first call.
#[tauri::command]
pub async fn engine_ping(
    app: AppHandle,
    state: State<'_, EngineState>,
) -> Result<Value, EngineError> {
    engine::request(&app, &state, "ping", serde_json::json!({})).await
}

/// Round-trips the sidecar's own `status` command (Python version, CadQuery
/// version, OCP variant, VTK-installed flag) — richer diagnostics than the
/// Rust-local `engine_status`, at the cost of an actual IPC round trip.
#[tauri::command]
pub async fn engine_sidecar_status(
    app: AppHandle,
    state: State<'_, EngineState>,
) -> Result<Value, EngineError> {
    engine::request(&app, &state, "status", serde_json::json!({})).await
}

/// Requests a real ZeroRod preview mesh and validates it Rust-side
/// (`mesh::validate_and_summarize`) before it ever reaches the frontend.
/// Returns a summary, not the raw geometry arrays — kept from M2 for
/// lightweight diagnostics (the "Ping Engine" / status-oriented use). M3's
/// actual Three.js consumer uses `engine_preview_mesh` below, which wants
/// the full payload.
#[tauri::command]
pub async fn engine_preview(
    app: AppHandle,
    state: State<'_, EngineState>,
) -> Result<mesh::MeshSummary, EngineError> {
    let payload = engine::request(&app, &state, "preview", serde_json::json!({})).await?;
    mesh::validate_and_summarize(&payload)
        .map_err(|problems| EngineError::new("invalid_mesh", problems.join("; ")))
}

/// M3: requests a real ZeroRod preview mesh, validates it Rust-side (same
/// `mesh::validate_and_summarize` check as `engine_preview` — no duplicated
/// validation logic), and returns the full validated `zerorod-mesh/v1`
/// payload so the frontend can build real `THREE.BufferGeometry` from it.
/// No new IPC protocol — same sidecar `preview` command, same
/// `zerorod-mesh/v1` schema `engine_preview` already validates; this
/// command only differs in what it returns to the WebView. Always requests
/// canonical defaults (empty parameters) — unchanged since Build 022;
/// `engine_preview_mesh_with_parameters` below is the M1 parameter-driven
/// sibling, kept as a separate command so this one's call sites (and
/// argument shape) never change.
#[tauri::command]
pub async fn engine_preview_mesh(
    app: AppHandle,
    state: State<'_, EngineState>,
) -> Result<Value, EngineError> {
    let payload = engine::request(&app, &state, "preview", serde_json::json!({})).await?;
    mesh::validate_and_summarize(&payload)
        .map_err(|problems| EngineError::new("invalid_mesh", problems.join("; ")))?;
    Ok(payload)
}

/// Build 023 M1: requests a ZeroRod preview mesh for an explicit
/// zerorod-parameters/v1 `parameters` object (forwarded verbatim to the
/// sidecar's `preview` command — see docs/contracts/ZEROROD-PARAMETERS-V1.md).
/// Same validation and return shape as `engine_preview_mesh`; the only
/// difference is that the caller supplies `parameters` instead of relying
/// on the sidecar's canonical defaults. Not wired into any UI control in
/// M1 — this is protocol/contract foundation only.
#[tauri::command]
pub async fn engine_preview_mesh_with_parameters(
    app: AppHandle,
    state: State<'_, EngineState>,
    parameters: Value,
) -> Result<Value, EngineError> {
    let payload = engine::request(&app, &state, "preview", parameters).await?;
    mesh::validate_and_summarize(&payload)
        .map_err(|problems| EngineError::new("invalid_mesh", problems.join("; ")))?;
    Ok(payload)
}

/// Build 023 M1: round-trips the sidecar's `parameters_defaults` command,
/// returning the canonical `ZeroRodParameters` default set wrapped in the
/// zerorod-parameters/v1 envelope — the single authoritative default source
/// a future frontend can consume instead of hardcoding a second copy (see
/// docs/contracts/ZEROROD-PARAMETERS-V1.md). Not wired into any UI in M1.
#[tauri::command]
pub async fn engine_parameters_defaults(
    app: AppHandle,
    state: State<'_, EngineState>,
) -> Result<Value, EngineError> {
    engine::request(&app, &state, "parameters_defaults", serde_json::json!({})).await
}

/// Build 024 M1: the one narrow filesystem-adjacent capability the WebView
/// gets — asking Rust to show the OS's own native directory picker and
/// relaying back only the single path the user chose (or `None` on
/// cancellation, distinguished from an error — see
/// docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md "Dialog cancellation").
/// The WebView never receives a directory-listing or file-read/write
/// capability itself; this command's only output is the opaque path string,
/// which the frontend can then pass back into `engine_export` unmodified.
/// Directory selection (not file selection) matches `export_project`'s own
/// shape — it always writes a fixed *set* of files into a chosen directory,
/// never a single chosen output file.
#[tauri::command]
pub async fn select_export_directory(app: AppHandle) -> Result<Option<String>, EngineError> {
    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .pick_folder(move |folder: Option<FilePath>| {
            let _ = tx.send(folder);
        });
    let folder = rx.await.map_err(|_| {
        EngineError::new(
            "dialog_channel_closed",
            "directory dialog callback channel closed before responding",
        )
    })?;
    Ok(folder.map(|path| path.to_string()))
}

/// Build 024 M1: requests the sidecar's `export` command for an explicit
/// zerorod-parameters/v1 `parameters` object (the caller's job to supply —
/// see docs/migration/BUILD-024-HANDOFF.md: the frontend's `accepted` state
/// is the intended source, not an arbitrary draft) and a `output_directory`
/// obtained from `select_export_directory` above (never a WebView-typed raw
/// path). Rust does not interpret either value — both are forwarded
/// verbatim inside a single combined object, matching how
/// `engine_preview_mesh_with_parameters` already forwards `parameters`
/// without inspecting its shape. Same serialized-request-queue behavior as
/// every other `engine::request` call: an export queues behind (or after) a
/// live-preview request already in flight, by construction, with no new
/// concurrency code.
#[tauri::command]
pub async fn engine_export(
    app: AppHandle,
    state: State<'_, EngineState>,
    parameters: Value,
    output_directory: String,
) -> Result<Value, EngineError> {
    let request_parameters = serde_json::json!({
        "parameters": parameters,
        "output_directory": output_directory,
    });
    engine::request(&app, &state, "export", request_parameters).await
}

/// Build 024 M2: pure, side-effect-free overwrite-conflict check for the
/// destination `engine_export` would write into — same request shape as
/// `engine_export` (parameters + output_directory), minus performing the
/// export itself. Rust does not interpret either value, exactly like
/// `engine_export`; the actual filename/conflict logic lives sidecar-side
/// (`export_preflight`, reusing `zerorodcad.export.expected_output_filenames`
/// — the same sanitization `export` itself uses, never duplicated here or
/// in the frontend). No directory enumeration crosses the IPC boundary,
/// only the fixed, known set of expected output filenames and which of them
/// already exist.
#[tauri::command]
pub async fn engine_export_preflight(
    app: AppHandle,
    state: State<'_, EngineState>,
    parameters: Value,
    output_directory: String,
) -> Result<Value, EngineError> {
    let request_parameters = serde_json::json!({
        "parameters": parameters,
        "output_directory": output_directory,
    });
    engine::request(&app, &state, "export_preflight", request_parameters).await
}

/// Explicit shutdown command (also invoked automatically on app exit — see
/// `lib.rs`'s `RunEvent::ExitRequested` handler).
#[tauri::command]
pub async fn engine_shutdown(state: State<'_, EngineState>) -> Result<(), EngineError> {
    engine::shutdown(&state).await;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_info_reports_build_022_m3() {
        let info = app_info();
        assert_eq!(info.build, "022");
        assert_eq!(info.milestone, "M3");
        assert!(!info.version.is_empty());
    }
}
