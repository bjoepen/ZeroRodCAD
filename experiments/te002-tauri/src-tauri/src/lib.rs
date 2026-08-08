// TE-002 / TE-002.1 PoC — intentionally minimal. All sidecar process
// control lives in Rust (`sidecar::request_preview` for the one-shot
// architecture, `persistent::persistent_preview`/`persistent_shutdown` for
// the TE-002.1 Variant C experiment) — the WebView only ever calls these
// narrow app commands over IPC; it has no direct shell/process permissions
// at all (section 28).

mod persistent;
mod sidecar;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(persistent::PersistentEngineState::default())
        .invoke_handler(tauri::generate_handler![
            sidecar::request_preview,
            persistent::persistent_preview,
            persistent::persistent_shutdown,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // TE-002.1 section 17: no sidecar process may outlive the app.
            // The one-shot `request_preview` command already awaits full
            // completion (or times out and kills) before returning, so it
            // never leaves anything running between calls; the persistent
            // engine is the one case that can have a live child process at
            // the moment the app exits, so it is explicitly killed here.
            if let tauri::RunEvent::ExitRequested { .. } = event {
                persistent::kill_if_running(app_handle);
            }
        });
}
