//! Build 022 M1 — the one Tauri command needed to prove the WebView -> Rust
//! IPC bridge works end to end, before M2 adds any sidecar/process logic.

use serde::Serialize;

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
        milestone: "M1".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_info_reports_build_022_m1() {
        let info = app_info();
        assert_eq!(info.build, "022");
        assert_eq!(info.milestone, "M1");
        assert!(!info.version.is_empty());
    }
}
