import { invoke } from "@tauri-apps/api/core";

export interface AppInfo {
  name: string;
  version: string;
  build: string;
  milestone: string;
}

/** Build 022 M1's one Tauri command: proves the WebView -> Rust IPC bridge
 * actually works end to end, before M2 adds any process/sidecar logic. */
export async function fetchAppInfo(): Promise<AppInfo> {
  return await invoke<AppInfo>("app_info");
}
