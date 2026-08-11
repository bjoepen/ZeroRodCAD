//! Tauri commands exposed to the WebView. `app_info` (M1) proves the IPC
//! bridge; the `engine_*` commands (M2/M3) are the only way the frontend
//! can reach the Python sidecar — all process control stays in `engine.rs`.

use serde::Serialize;
use serde_json::Value;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::{DialogExt, FilePath};

use crate::engine::{self, EngineState, EngineStatusInfo};
use crate::export_result::{validate_export_preflight_result, validate_export_result};
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
///
/// Build 024 M2 bugfix: `#[tauri::command]`'s default argument binding
/// expects the JS invoke() payload's keys in camelCase, derived from each
/// Rust parameter name (so a plain `#[tauri::command]` here would require
/// the frontend to send `outputDirectory`, not `output_directory`) — a
/// mismatch Human Validation caught as a real runtime
/// `missing required key outputDirectory` error, since `export.ts`'s
/// `requestExport`/`requestExportPreflight` (correctly, matching every JSON
/// field name elsewhere in this app's `zerorod-parameters/v1`/
/// `zerorod-sidecar/v1` contracts, and the very `"output_directory"` JSON
/// key this function forwards to the sidecar two lines below) send
/// `output_directory`. `rename_all = "snake_case"` makes the invoke-argument
/// binding match the app's one existing wire convention instead of
/// introducing a second, camelCase one only at this boundary.
#[tauri::command(rename_all = "snake_case")]
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
    let payload = engine::request(&app, &state, "export", request_parameters).await?;
    // Build 024 M3: the sidecar is a trusted local process, but nothing
    // previously checked the *shape* of its export result before relaying
    // it to the WebView as a success value — a missing/wrong-typed field
    // would have reached the frontend's success-rendering path unchecked.
    // Mirrors `engine_preview_mesh`'s existing `mesh::validate_and_summarize`
    // guard for the same reason: a malformed result must never read as
    // success (docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md).
    validate_export_result(&payload)
        .map_err(|problems| EngineError::new("invalid_export_result", problems.join("; ")))?;
    Ok(payload)
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
///
/// Same `rename_all = "snake_case"` bugfix as `engine_export` above (see its
/// doc comment) — this command has the identical `output_directory`
/// argument and was affected by the identical defect.
#[tauri::command(rename_all = "snake_case")]
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
    let payload = engine::request(&app, &state, "export_preflight", request_parameters).await?;
    // Build 024 M3: same structural-validation guard as `engine_export`
    // above — see its doc comment.
    validate_export_preflight_result(&payload)
        .map_err(|problems| EngineError::new("invalid_export_result", problems.join("; ")))?;
    Ok(payload)
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

    // Build 024 M2 bugfix regression tests — real IPC dispatch through
    // Tauri's actual generated command deserializer
    // (`tauri::test::get_ipc_response`), not a mocked helper one layer
    // below the actual invoke() call.
    //
    // The original defect (`missing required key outputDirectory`) was
    // invisible to every prior test because the frontend's own tests mock
    // `@tauri-apps/api/core`'s `invoke()` entirely (proving only what our
    // TypeScript *sends*, never what Tauri's generated command deserializer
    // actually *accepts*), and no Rust test exercised the real
    // `#[tauri::command]`-generated argument binding at all.
    //
    // These tests cannot dispatch `engine_export`/`engine_export_preflight`
    // literally: both take `app: AppHandle` (the plain, non-generic alias,
    // which — like every other command in this file — resolves to
    // `AppHandle<Wry>`, since `engine::request` itself is written against
    // the concrete `AppHandle`/`EngineState`, and `engine.rs` is a
    // deliberately unchanged invariant this repository's own validation
    // gates check across builds). `tauri::test::get_ipc_response` requires
    // `MockRuntime`, which `AppHandle<Wry>` cannot satisfy — so, rather than
    // making `engine.rs` generic over `Runtime` purely to make this
    // testable (a real architectural change well outside a narrow
    // argument-binding bugfix), this test dispatches a local twin command
    // with the *exact* same `#[tauri::command(rename_all = "snake_case")]`
    // attribute and the *exact* same `(parameters: Value, output_directory:
    // String)` parameter list/types as both real commands — proving the
    // real mechanism that broke (macro-attribute + parameter-name
    // combination) accepts export.ts's real payload and rejects the
    // camelCase variant, through the real IPC dispatch path, without
    // re-testing (or duplicating any logic of) the sidecar call itself.
    mod ipc_argument_binding {
        use tauri::ipc::{CallbackFn, InvokeBody};
        use tauri::test::{get_ipc_response, mock_builder, mock_context, noop_assets, INVOKE_KEY};
        use tauri::webview::InvokeRequest;
        use tauri::WebviewWindowBuilder;

        /// Byte-for-byte the same attribute and argument list as
        /// `engine_export`/`engine_export_preflight` in this file — see the
        /// module doc comment above for why a twin command, not the literal
        /// production one, is what's dispatched here.
        #[tauri::command(rename_all = "snake_case")]
        fn export_args_binding_twin(
            parameters: serde_json::Value,
            output_directory: String,
        ) -> serde_json::Value {
            serde_json::json!({"parameters": parameters, "output_directory": output_directory})
        }

        fn dispatch(body: serde_json::Value) -> Result<serde_json::Value, serde_json::Value> {
            let app = mock_builder()
                .invoke_handler(tauri::generate_handler![export_args_binding_twin])
                .build(mock_context(noop_assets()))
                .unwrap();
            let webview = WebviewWindowBuilder::new(&app, "main", Default::default())
                .build()
                .unwrap();

            let request = InvokeRequest {
                cmd: "export_args_binding_twin".into(),
                callback: CallbackFn(0),
                error: CallbackFn(1),
                // `tauri://localhost` (not `http://tauri.localhost`) is
                // what `mock_context`'s `MockRuntime` actually recognizes
                // as the local origin (confirmed against tauri's own
                // `remote_origin_blocked_for_custom_commands_without_app_manifest`
                // test in webview/mod.rs) — a remote-looking origin here
                // would make ACL enforcement kick in and reject even a
                // correctly-shaped payload for an unrelated reason.
                url: "tauri://localhost".parse().unwrap(),
                body: InvokeBody::from(body),
                headers: Default::default(),
                invoke_key: INVOKE_KEY.to_string(),
            };

            get_ipc_response(&webview, request)
                .map(|response_body| response_body.deserialize::<serde_json::Value>().unwrap())
        }

        #[test]
        fn accepts_the_exact_payload_export_ts_sends_for_preflight_and_export() {
            // Mirrors desktop/frontend/src/export.ts's requestExport /
            // requestExportPreflight invoke() calls byte-for-byte:
            // {"parameters": ..., "output_directory": ...}.
            let body = serde_json::json!({
                "parameters": {"schema": "zerorod-parameters/v1", "values": {}},
                "output_directory": "/tmp/zerorodcad-test-export",
            });
            let result =
                dispatch(body.clone()).expect("export.ts's real payload shape must be accepted");
            assert_eq!(result["output_directory"], "/tmp/zerorodcad-test-export");
            assert_eq!(result["parameters"], body["parameters"]);
        }

        #[test]
        fn rejects_camel_case_output_directory() {
            // Locks down the one canonical (snake_case) invocation shape —
            // proves `rename_all = "snake_case"` is actually in effect,
            // rather than Tauri's default camelCase binding silently still
            // being accepted alongside (or instead of) it. This is exactly
            // the payload shape a naive Tauri-default-convention frontend
            // change could reintroduce.
            let body = serde_json::json!({
                "parameters": {"schema": "zerorod-parameters/v1", "values": {}},
                "outputDirectory": "/tmp/zerorodcad-test-export",
            });
            let error = dispatch(body).expect_err("camelCase outputDirectory must be rejected");
            let message = error.as_str().unwrap_or_default();
            assert!(
                message.contains("output_directory"),
                "expected an argument-binding error naming output_directory, got: {message}"
            );
        }

        #[test]
        fn rejects_a_missing_output_directory() {
            let body = serde_json::json!({
                "parameters": {"schema": "zerorod-parameters/v1", "values": {}},
            });
            let error =
                dispatch(body).expect_err("a missing output_directory key must be rejected");
            assert!(error
                .as_str()
                .unwrap_or_default()
                .contains("output_directory"));
        }
    }
}
