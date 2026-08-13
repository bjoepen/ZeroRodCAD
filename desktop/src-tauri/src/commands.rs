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

// Build 025 M1 identity fix: this pair (`build`/`milestone`) is the single
// source of truth for the app's visible build/milestone identity — nowhere
// else hardcodes it (diagnostics_panel.ts, Build 025 M2's relocation of the
// old status panel, is the only renderer, reading these two fields; before
// that, main.ts's status panel used to also carry a second,
// independently-drifting copy in a static subtitle string, which was the
// actual cause of the Project Owner seeing a stale "Build 024 — Milestone
// 2" label while validating the M1 build — see docs/migration/
// BUILD-025-M1-ARTIFACT-IDENTITY-FIX.md).
//
// Build 025 M3 process correction: despite the instruction above, this
// value was NOT bumped for M2 — it kept reading "M1" through the entire M2
// milestone, including its shipped Human Validation artifact. M2's own
// validate-build025-m2.sh gate made this worse, not better: it asserted
// milestone == "M1" (i.e. "unchanged since M1") as a deliberate,
// rationalized "STALE_GATE_ASSUMPTION", rather than asserting what should
// actually have been true for an M2 gate (milestone == "M2"). Lesson: a
// milestone's own validation gate must assert ITS OWN milestone value, not
// "whatever the field already said" — the latter can never catch a missed
// bump, by construction, since it always trivially agrees with the status
// quo. See the `app_info_reports_current_milestone`/
// `app_info_never_reports_a_stale_milestone` tests below and
// `scripts/validate-build025-m3.sh`, which both now hardcode "M3"
// specifically for this reason. Update both fields together, here only, at
// the start of each new milestone.
#[tauri::command]
pub fn app_info() -> AppInfo {
    AppInfo {
        name: "ZeroRodCAD Desktop".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        build: "025".to_string(),
        milestone: "M4".to_string(),
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

/// Build 025 M3 — structural validation for the `report` command's result,
/// mirroring `mesh::validate_and_summarize`'s "never trust a raw sidecar
/// payload" discipline (a much smaller check than `mesh.rs`/
/// `export_result.rs` need, since the report result has exactly one field
/// to verify): a malformed/missing `markdown` string must never reach the
/// WebView as a false success.
fn validate_report_result(payload: &Value) -> Result<(), String> {
    match payload.get("markdown") {
        Some(Value::String(markdown)) if !markdown.is_empty() => Ok(()),
        Some(Value::String(_)) => Err("report result 'markdown' must not be empty".to_string()),
        Some(_) => Err("report result 'markdown' must be a string".to_string()),
        None => Err("report result missing 'markdown'".to_string()),
    }
}

/// Build 025 M3 — requests the Instrument Report (§16-23 of the mandate)
/// for an explicit zerorod-parameters/v1 `parameters` object, exactly the
/// same shape `engine_preview_mesh_with_parameters` already forwards
/// verbatim (see docs/contracts/ZEROROD-PARAMETERS-V1.md's `report`
/// command section). The frontend's intended source is `accepted`, the
/// same "what you see is what the report describes" rule §18 restates from
/// export's own precedent — this command does not itself decide which
/// parameter state to use, same division of responsibility as export.
#[tauri::command]
pub async fn engine_report(
    app: AppHandle,
    state: State<'_, EngineState>,
    parameters: Value,
) -> Result<Value, EngineError> {
    let payload = engine::request(&app, &state, "report", parameters).await?;
    validate_report_result(&payload)
        .map_err(|problem| EngineError::new("invalid_report_result", problem))?;
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

/// Build 025 M1: shows the OS's native file-open dialog, filtered to
/// `.zerorod` project files, and returns the chosen path (or `None` on
/// cancellation — same non-error cancellation convention as
/// `select_export_directory`). Uses the same `dialog:allow-open` capability
/// `select_export_directory` already has — `tauri-plugin-dialog`'s ACL
/// gates the whole `open` command, not file-vs-folder pickers separately
/// (confirmed against the vendored plugin's `permissions/autogenerated/
/// commands/open.toml`), so no new capability grant is needed for this one.
#[tauri::command]
pub async fn select_project_open_file(app: AppHandle) -> Result<Option<String>, EngineError> {
    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .add_filter("ZeroRodCAD Project", &["zerorod"])
        .pick_file(move |file: Option<FilePath>| {
            let _ = tx.send(file);
        });
    let file = rx.await.map_err(|_| {
        EngineError::new(
            "dialog_channel_closed",
            "open dialog callback channel closed before responding",
        )
    })?;
    Ok(file.map(|path| path.to_string()))
}

/// Build 025 M1: shows the OS's native save dialog, filtered to `.zerorod`,
/// pre-filled with `default_file_name` (Save As's default filename — see
/// `docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md`), and returns the
/// chosen path (or `None` on cancellation). Genuinely new WebView-reachable
/// capability, `dialog:allow-save` — Build 024 never needed a save dialog
/// (export always writes a fixed set of files into a chosen *directory*).
/// Narrowly scoped exactly like `dialog:allow-open` was in Build 024 M1: the
/// WebView receives only the opaque chosen path back, never gains
/// filesystem read/write/list capability itself — the actual file write
/// stays sidecar-owned (`engine_project_save` below).
#[tauri::command(rename_all = "snake_case")]
pub async fn select_project_save_file(
    app: AppHandle,
    default_file_name: String,
) -> Result<Option<String>, EngineError> {
    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .add_filter("ZeroRodCAD Project", &["zerorod"])
        .set_file_name(default_file_name)
        .save_file(move |file: Option<FilePath>| {
            let _ = tx.send(file);
        });
    let file = rx.await.map_err(|_| {
        EngineError::new(
            "dialog_channel_closed",
            "save dialog callback channel closed before responding",
        )
    })?;
    Ok(file.map(|path| path.to_string()))
}

/// Build 025 M1: requests the sidecar's `project_open` command for a
/// `path` obtained from `select_project_open_file` above (never a
/// WebView-typed raw path). Returns the loaded project's parameters wrapped
/// in the zerorod-parameters/v1 envelope (`{schema, values}`) — the same
/// shape `engine_parameters_defaults` already returns unvalidated
/// Rust-side, which this command follows as its closest precedent: the
/// sidecar has already run structural (Level 1/2), domain (Level 3)
/// validation before returning, and a malformed response would fail to
/// deserialize into a `zerorod-parameters/v1` shape the frontend's own
/// `validateParametersShape` already checks, so no second Rust-side
/// structural-validation module was added here (see
/// docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md "Result validation").
#[tauri::command(rename_all = "snake_case")]
pub async fn engine_project_open(
    app: AppHandle,
    state: State<'_, EngineState>,
    path: String,
) -> Result<Value, EngineError> {
    let request_parameters = serde_json::json!({ "path": path });
    engine::request(&app, &state, "project_open", request_parameters).await
}

/// Build 025 M1: requests the sidecar's `project_save` command for an
/// explicit zerorod-parameters/v1 `parameters` object (the caller's job to
/// supply — always the frontend's `accepted` state, never the draft, per
/// `docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md` "Canonical Save
/// State") and a `path` (either the project's existing `current_path`, or
/// one obtained from `select_project_save_file`). Rust does not interpret
/// either value, exactly like `engine_export` does not interpret
/// `parameters`/`output_directory`.
#[tauri::command(rename_all = "snake_case")]
pub async fn engine_project_save(
    app: AppHandle,
    state: State<'_, EngineState>,
    parameters: Value,
    path: String,
) -> Result<Value, EngineError> {
    let request_parameters = serde_json::json!({
        "parameters": parameters,
        "path": path,
    });
    engine::request(&app, &state, "project_save", request_parameters).await
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
    fn app_info_reports_current_milestone() {
        let info = app_info();
        assert_eq!(info.build, "025");
        assert_eq!(info.milestone, "M4");
        assert!(!info.version.is_empty());
    }

    // Build 025 M1 artifact-identity-fix regression: the specific stale
    // pair the Project Owner actually saw in the built .app must never come
    // back together (each value alone is fine in other contexts — e.g. a
    // doc comment — the *pair*, as what app_info() reports, is the bug).
    #[test]
    fn app_info_never_reports_a_stale_024_m2_pair() {
        let info = app_info();
        assert!(
            !(info.build == "024" && info.milestone == "M2"),
            "app_info() must not report the stale Build 024 / M2 identity"
        );
    }

    // Build 025 M3 process correction: M2 shipped its entire Human
    // Validation artifact still silently reporting milestone "M1" — a
    // forgotten-bump defect a value-pinning test alone cannot prevent
    // (updating the pinned value and forgetting the real bump are the same
    // mistake). This is the general form of that check: an M3 (or later)
    // artifact must never report an EARLIER Build 025 milestone, not just
    // the one specific pair already caught above.
    #[test]
    fn app_info_never_reports_a_stale_earlier_build_025_milestone() {
        let info = app_info();
        assert_eq!(info.build, "025");
        assert!(
            !["M1", "M2", "M3"].contains(&info.milestone.as_str()),
            "app_info() must not report an earlier Build 025 milestone ({}); \
             this is the exact class of defect that shipped M2 still \
             reporting M1",
            info.milestone
        );
    }

    // Build 025 M3 — `validate_report_result` (the `engine_report` command's
    // "never trust a raw sidecar payload" structural check, mirroring
    // `mesh::validate_and_summarize`/`export_result.rs`).
    #[test]
    fn validate_report_result_accepts_a_well_formed_payload() {
        let payload = serde_json::json!({"markdown": "# Instrument Report – CBG Open G"});
        assert!(validate_report_result(&payload).is_ok());
    }

    #[test]
    fn validate_report_result_rejects_a_missing_markdown_field() {
        let payload = serde_json::json!({});
        assert!(validate_report_result(&payload).is_err());
    }

    #[test]
    fn validate_report_result_rejects_a_non_string_markdown_field() {
        let payload = serde_json::json!({"markdown": 42});
        assert!(validate_report_result(&payload).is_err());
    }

    #[test]
    fn validate_report_result_rejects_an_empty_markdown_string() {
        let payload = serde_json::json!({"markdown": ""});
        assert!(validate_report_result(&payload).is_err());
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

        /// Byte-for-byte the same attribute and argument list as
        /// `select_project_save_file` in this file (Build 025 M1).
        #[tauri::command(rename_all = "snake_case")]
        fn project_save_file_args_binding_twin(default_file_name: String) -> serde_json::Value {
            serde_json::json!({"default_file_name": default_file_name})
        }

        /// Byte-for-byte the same attribute and argument list as
        /// `engine_project_open` in this file (Build 025 M1).
        #[tauri::command(rename_all = "snake_case")]
        fn project_open_args_binding_twin(path: String) -> serde_json::Value {
            serde_json::json!({"path": path})
        }

        /// Byte-for-byte the same attribute and argument list as
        /// `engine_project_save` in this file (Build 025 M1) — the same
        /// `parameters` + a second, underscore-named argument shape as
        /// `engine_export`, so this is exactly the bug class Build 024 M2
        /// found, proactively regression-tested from the start rather than
        /// waiting for Human Validation to catch it again (see
        /// [[feedback-tauri-command-arg-casing]] in project memory).
        #[tauri::command(rename_all = "snake_case")]
        fn project_save_args_binding_twin(
            parameters: serde_json::Value,
            path: String,
        ) -> serde_json::Value {
            serde_json::json!({"parameters": parameters, "path": path})
        }

        /// Byte-for-byte the same attribute and argument list as
        /// `engine_report` in this file (Build 025 M3) — a single-word
        /// argument name has no camelCase/snake_case ambiguity, so this is
        /// mainly a contract-shape regression (report.ts's real `invoke()`
        /// payload is accepted end to end), not a casing-bug guard like the
        /// twins above.
        #[tauri::command(rename_all = "snake_case")]
        fn report_args_binding_twin(parameters: serde_json::Value) -> serde_json::Value {
            serde_json::json!({"parameters": parameters})
        }

        fn dispatch(
            cmd: &str,
            body: serde_json::Value,
        ) -> Result<serde_json::Value, serde_json::Value> {
            let app = mock_builder()
                .invoke_handler(tauri::generate_handler![
                    export_args_binding_twin,
                    project_save_file_args_binding_twin,
                    project_open_args_binding_twin,
                    project_save_args_binding_twin,
                    report_args_binding_twin,
                ])
                .build(mock_context(noop_assets()))
                .unwrap();
            let webview = WebviewWindowBuilder::new(&app, "main", Default::default())
                .build()
                .unwrap();

            let request = InvokeRequest {
                cmd: cmd.into(),
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
            let result = dispatch("export_args_binding_twin", body.clone())
                .expect("export.ts's real payload shape must be accepted");
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
            let error = dispatch("export_args_binding_twin", body)
                .expect_err("camelCase outputDirectory must be rejected");
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
            let error = dispatch("export_args_binding_twin", body)
                .expect_err("a missing output_directory key must be rejected");
            assert!(error
                .as_str()
                .unwrap_or_default()
                .contains("output_directory"));
        }

        // --- Build 025 M1: project persistence argument binding ---------

        #[test]
        fn accepts_the_exact_payload_project_ts_sends_for_save_file_dialog() {
            let body = serde_json::json!({"default_file_name": "cbg-open-g.zerorod"});
            let result = dispatch("project_save_file_args_binding_twin", body)
                .expect("project.ts's real save-dialog payload shape must be accepted");
            assert_eq!(result["default_file_name"], "cbg-open-g.zerorod");
        }

        #[test]
        fn rejects_camel_case_default_file_name() {
            let body = serde_json::json!({"defaultFileName": "cbg-open-g.zerorod"});
            let error = dispatch("project_save_file_args_binding_twin", body)
                .expect_err("camelCase defaultFileName must be rejected");
            assert!(error
                .as_str()
                .unwrap_or_default()
                .contains("default_file_name"));
        }

        #[test]
        fn accepts_the_exact_payload_project_ts_sends_for_open() {
            let body = serde_json::json!({"path": "/tmp/zerorodcad-test/project.zerorod"});
            let result = dispatch("project_open_args_binding_twin", body)
                .expect("project.ts's real open payload shape must be accepted");
            assert_eq!(result["path"], "/tmp/zerorodcad-test/project.zerorod");
        }

        #[test]
        fn rejects_a_missing_path_for_open() {
            let error = dispatch("project_open_args_binding_twin", serde_json::json!({}))
                .expect_err("a missing path key must be rejected");
            assert!(error.as_str().unwrap_or_default().contains("path"));
        }

        #[test]
        fn accepts_the_exact_payload_project_ts_sends_for_save() {
            let body = serde_json::json!({
                "parameters": {"schema": "zerorod-parameters/v1", "values": {}},
                "path": "/tmp/zerorodcad-test/project.zerorod",
            });
            let result = dispatch("project_save_args_binding_twin", body.clone())
                .expect("project.ts's real save payload shape must be accepted");
            assert_eq!(result["path"], "/tmp/zerorodcad-test/project.zerorod");
            assert_eq!(result["parameters"], body["parameters"]);
        }

        #[test]
        fn rejects_camel_case_path_arguments_are_not_a_concern_but_missing_path_is_rejected_for_save(
        ) {
            // `path` has no case-ambiguity risk (`rename_all = "snake_case"`
            // and camelCase are identical for a single-word argument name,
            // unlike `output_directory`/`outputDirectory` or
            // `default_file_name`/`defaultFileName`) — the real regression
            // risk for this command is the same as `engine_export`'s
            // (a missing required key), covered here.
            let body = serde_json::json!({
                "parameters": {"schema": "zerorod-parameters/v1", "values": {}},
            });
            let error = dispatch("project_save_args_binding_twin", body)
                .expect_err("a missing path key must be rejected");
            assert!(error.as_str().unwrap_or_default().contains("path"));
        }

        // --- Build 025 M3: Instrument Report argument binding -----------

        #[test]
        fn accepts_the_exact_payload_report_ts_sends() {
            let body = serde_json::json!({
                "parameters": {"schema": "zerorod-parameters/v1", "values": {}},
            });
            let result = dispatch("report_args_binding_twin", body.clone())
                .expect("report.ts's real payload shape must be accepted");
            assert_eq!(result["parameters"], body["parameters"]);
        }
    }
}
