// TE-002 PoC — intentionally minimal. All sidecar process control lives in
// `sidecar::request_preview` (Rust), not the frontend (section 17). The
// WebView only ever calls this one narrow app command over IPC; it has no
// direct shell/process permissions at all (section 28).

mod sidecar;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![sidecar::request_preview])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
