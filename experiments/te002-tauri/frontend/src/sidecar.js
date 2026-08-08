// TE-002 — frontend side of the sidecar bridge (sections 17-18).
// The frontend never spawns a process or talks to the shell plugin
// directly; it only calls the app's own `request_preview` Tauri command,
// which does all process control and protocol handling in Rust
// (see src-tauri/src/sidecar.rs). This keeps the WebView's IPC surface to
// exactly one narrow, app-specific command (section 28).

import { invoke } from "@tauri-apps/api/core";

export class SidecarTimeoutError extends Error {}
export class SidecarProcessError extends Error {}

/**
 * Requests a ZeroRod preview mesh from the Python sidecar via the Rust
 * `request_preview` command. Resolves with the `zerorod-mesh/v1` result, or
 * throws SidecarTimeoutError / SidecarProcessError with the structured
 * `{code, message}` the Rust side reports.
 */
export async function requestPreview() {
  try {
    return await invoke("request_preview");
  } catch (error) {
    const code = error?.code ?? "unknown_error";
    const message = error?.message ?? String(error);
    if (code === "timeout") {
      throw new SidecarTimeoutError(message);
    }
    throw new SidecarProcessError(`${code}: ${message}`);
  }
}
