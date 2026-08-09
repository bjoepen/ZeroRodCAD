// ZeroRodCAD Desktop 2.0 — productive Tauri v2 shell (Build 022).
//
// M1 establishes the shell itself and one command (`app_info`) proving the
// WebView -> Rust IPC bridge works. M2 adds `mod engine`/`mod protocol` and
// the sidecar lifecycle commands; nothing about the sidecar/process
// architecture is implemented yet.

mod commands;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![commands::app_info])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, _event| {});
}
