// ZeroRodCAD Desktop 2.0 — productive Tauri v2 shell (Build 022).
//
// M1 established the shell itself and the WebView -> Rust IPC bridge
// (`app_info`). M2 adds the persistent Python sidecar's process/IPC layer
// (`engine`/`protocol`/`mesh`) and its Tauri commands — no Three.js
// rendering, parameter UI, or export UI yet (M3+/Build 023-024).

mod commands;
mod engine;
mod mesh;
mod protocol;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(engine::EngineState::default())
        .invoke_handler(tauri::generate_handler![
            commands::app_info,
            commands::engine_status,
            commands::engine_ping,
            commands::engine_sidecar_status,
            commands::engine_preview,
            commands::engine_shutdown,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // No sidecar process may outlive the app (TE-002.1 section 17).
            // Every engine_* command already awaits full completion (or
            // times out and kills) before returning, so nothing is left
            // running between calls; the persistent engine is the one case
            // that can have a live child process at the moment the app
            // exits, so it is explicitly killed here.
            if let tauri::RunEvent::ExitRequested { .. } = event {
                engine::kill_if_running(app_handle);
            }
        });
}
