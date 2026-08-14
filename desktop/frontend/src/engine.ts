import { invoke } from "@tauri-apps/api/core";
import type { MeshPayload } from "./mesh";

// Mirrors desktop/src-tauri/src/protocol.rs's EngineError — the frontend
// only ever sees these, never a raw Python traceback (zerorod-sidecar/v1
// forbids that at the source). `details` (Build 023 M1) carries optional
// structured context (e.g. `field`/`expected`/`actual` for a
// zerorod-parameters/v1 validation failure) — omitted when the sidecar
// didn't provide any, exactly like Rust's `#[serde(skip_serializing_if)]`.
export interface EngineError {
  code: string;
  message: string;
  details?: unknown;
}

export type LifecycleState = "STOPPED" | "RUNNING" | "ERROR";

// Mirrors desktop/src-tauri/src/engine.rs's EngineStatusInfo.
export interface EngineStatusInfo {
  state: LifecycleState;
  pid: number | null;
  last_error: EngineError | null;
}

export interface PingResult {
  status: string;
  pid: number;
}

export interface SidecarStatus {
  status: string;
  pid: number;
  python_version: string;
  cadquery_version: string | null;
  ocp_variant: string | null;
  vtk_installed: boolean;
}

// Mirrors desktop/src-tauri/src/mesh.rs's MeshSummary — a summary, not the
// raw geometry arrays. M2 proves the engine data path end to end; M3 is the
// actual Three.js consumer that will want the full payload.
export interface MeshSummary {
  schema: string;
  mesh_count: number;
  total_vertices: number;
  total_triangles: number;
  line_count: number;
  bounds: unknown;
}

export function isEngineError(error: unknown): error is EngineError {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error
  );
}

/** Rust-local lifecycle status — instant, does not itself talk to the sidecar. */
export async function fetchEngineStatus(): Promise<EngineStatusInfo> {
  return await invoke<EngineStatusInfo>("engine_status");
}

/** Round-trips the sidecar's `ping` command; starts the sidecar lazily on first call. */
export async function pingEngine(): Promise<PingResult> {
  return await invoke<PingResult>("engine_ping");
}

/** Round-trips the sidecar's own `status` command for richer diagnostics. */
export async function fetchSidecarStatus(): Promise<SidecarStatus> {
  return await invoke<SidecarStatus>("engine_sidecar_status");
}

/** Requests a real ZeroRod preview mesh; validated Rust-side before it reaches here. */
export async function requestPreviewSummary(): Promise<MeshSummary> {
  return await invoke<MeshSummary>("engine_preview");
}

/** M3: requests a real ZeroRod preview mesh and returns the full
 * zerorod-mesh/v1 payload (validated Rust-side, same check as
 * requestPreviewSummary) for the Three.js consumer to render. */
export async function requestPreviewMesh(): Promise<MeshPayload> {
  return await invoke<MeshPayload>("engine_preview_mesh");
}

/** Explicit shutdown — also happens automatically on app exit. */
export async function shutdownEngine(): Promise<void> {
  await invoke("engine_shutdown");
}
