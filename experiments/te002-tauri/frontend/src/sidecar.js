// TE-002 / TE-002.1 — frontend side of the sidecar bridge (sections 17-18).
// The frontend never spawns a process or talks to the shell plugin
// directly; it only calls the app's own Tauri commands, which do all
// process control and protocol handling in Rust (see
// src-tauri/src/sidecar.rs and src-tauri/src/persistent.rs). This keeps the
// WebView's IPC surface to a small number of narrow, app-specific commands
// (section 28) — never a general shell/process permission.
//
// TE-002.1 measured three deployment/runtime strategies (onefile one-shot,
// onedir one-shot, persistent) and found persistent+onedir clearly best
// (see docs/research/TE-002.1-Sidecar-Runtime/Results.md) — this is now the
// default path (`requestPreview`). The original TE-002 one-shot command
// (`request_preview`, onefile-packaged) is kept working and callable
// (`requestPreviewOneShot`) purely as a reference/fallback, not removed.

import { invoke } from "@tauri-apps/api/core";

export class SidecarTimeoutError extends Error {}
export class SidecarProcessError extends Error {}

function wrapInvokeError(error) {
  const code = error?.code ?? "unknown_error";
  const message = error?.message ?? String(error);
  if (code === "timeout") {
    return new SidecarTimeoutError(message);
  }
  return new SidecarProcessError(`${code}: ${message}`);
}

/**
 * TE-002.1 default: requests a ZeroRod preview mesh via the persistent
 * engine (`persistent_preview`). The first call starts the sidecar once;
 * subsequent calls reuse the already-running process (warm requests measured
 * at ~130ms median, versus a fresh onefile process's ~15s cold start).
 */
export async function requestPreview() {
  try {
    return await invoke("persistent_preview");
  } catch (error) {
    throw wrapInvokeError(error);
  }
}

/** Explicit persistent-engine shutdown (also happens automatically on app exit). */
export async function shutdownPersistentEngine() {
  try {
    await invoke("persistent_shutdown");
  } catch (error) {
    throw wrapInvokeError(error);
  }
}

/** TE-002's original one-shot path (onefile-packaged `externalBin` sidecar) — kept as a reference/fallback, not the default. */
export async function requestPreviewOneShot() {
  try {
    return await invoke("request_preview");
  } catch (error) {
    throw wrapInvokeError(error);
  }
}
