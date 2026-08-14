// ZeroRodCAD Desktop 2.0 — productive Tauri v2 shell (Build 022).
//
// M1 established the shell itself and the WebView -> Rust IPC bridge
// (`app_info`). M2 added the persistent Python sidecar's process/IPC layer
// (`engine`/`protocol`/`mesh`) and its Tauri commands. M3 adds one more
// command (`engine_preview_mesh`, returning the full validated mesh payload)
// so the frontend's Three.js consumer has something to render. Build 024 M1
// adds the export command boundary (`engine_export`) and the one narrow
// native-dialog command (`select_export_directory`) that lets the WebView
// obtain a user-chosen filesystem path without ever receiving filesystem
// permission itself — see docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md.
// Build 024 M3 adds `export_result`, structurally validating the sidecar's
// export/export_preflight results before they ever reach the WebView as a
// success value (mirroring `mesh`'s existing `validate_and_summarize`
// pattern) — see docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md.
// Build 025 M1 adds project persistence: `select_project_open_file`/
// `select_project_save_file` (the narrow native-dialog commands — the
// latter needs a new `dialog:allow-save` capability, the former reuses
// Build 024 M1's `dialog:allow-open`) and `engine_project_open`/
// `engine_project_save` (the sidecar command boundary, reusing
// `zerorodcad.project` unmodified) — see
// docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md. Build 025 M3 adds
// `engine_report` (the Instrument Report command boundary, reusing
// `zerorodcad.report.build_report` unmodified — no new WebView capability)
// — see docs/migration/BUILD-025-M3-PREVIEW-REPORT-PARITY.md. Build 025 M4
// adds the native macOS application menu (`menu` module) — replacing the
// implicit default menu (whose predefined Quit item bypassed the
// unsaved-changes guard, per the M1 native-close finding) with an explicit
// one whose Quit item resumes through the same validated window-close
// pipeline — and one new command, `menu::set_view_menu_checked` (mirrors a
// visible-UI-driven visibility change into the native View menu's checked
// state; no new WebView capability, see that module's doc comment) — see
// docs/migration/BUILD-025-M4-DESKTOP-SHELL.md.

mod commands;
mod engine;
mod export_result;
// `pub` only so tests/native_menu.rs (a separate compilation unit — see its
// own doc comment for why it can't share lib.rs's single
// `generate_context!()` call) can build the real menu tree directly rather
// than through IPC, which menu construction isn't.
pub mod menu;
mod mesh;
mod protocol;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(engine::EngineState::default())
        .menu(menu::build_menu)
        .on_menu_event(menu::handle_menu_event)
        .invoke_handler(tauri::generate_handler![
            commands::app_info,
            commands::engine_status,
            commands::engine_ping,
            commands::engine_sidecar_status,
            commands::engine_preview,
            commands::engine_preview_mesh,
            commands::engine_preview_mesh_with_parameters,
            commands::engine_report,
            commands::engine_parameters_defaults,
            commands::engine_export,
            commands::engine_export_preflight,
            commands::select_export_directory,
            commands::select_project_open_file,
            commands::select_project_save_file,
            commands::engine_project_open,
            commands::engine_project_save,
            commands::engine_shutdown,
            menu::set_view_menu_checked,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // No sidecar process may outlive the app (TE-002.1 section 17).
            // Every engine_* command already awaits full completion (or
            // times out and kills) before returning, so nothing is left
            // running between calls; the persistent engine is the one case
            // that can have a live child process at the moment the app
            // exits, so it is explicitly killed here. Build 025 M4: this is
            // unchanged — native Quit reaches the same window-close ->
            // ExitRequested chain the red close button always has (see
            // menu.rs's module doc comment), so no second shutdown path was
            // added here.
            if let tauri::RunEvent::ExitRequested { .. } = event {
                engine::kill_if_running(app_handle);
            }
        });
}
