// Build 025 M1 — project persistence protocol foundation.
//
// Mirrors export.ts's style: thin invoke() wrappers around the four new
// Rust commands (select_project_open_file, select_project_save_file,
// engine_project_open, engine_project_save). No UI, no session state (that
// is project_state.ts's job) — this module only proves the WebView-side
// call shape compiles and round-trips correctly against the real commands.

import { invoke } from "@tauri-apps/api/core";
import { buildParametersRequest, type ZeroRodParametersValues } from "./parameters";

export interface ProjectOpenResult {
  values: ZeroRodParametersValues;
}

export interface ProjectSaveResult {
  path: string;
}

/** Shows the OS's native file-open dialog, filtered to `.zerorod` project
 * files, via the Rust-owned `select_project_open_file` command, and returns
 * the chosen path, or `null` if the user cancelled — cancellation is a
 * normal, non-error outcome (same convention as `selectExportDirectory`),
 * never thrown as an EngineError. The WebView never browses a directory
 * itself; this is the only path information it ever receives. */
export async function selectProjectOpenFile(): Promise<string | null> {
  return await invoke<string | null>("select_project_open_file");
}

/** Shows the OS's native save dialog, filtered to `.zerorod`, pre-filled
 * with `defaultFileName`, via the Rust-owned `select_project_save_file`
 * command, and returns the chosen path, or `null` on cancellation. */
export async function selectProjectSaveFile(defaultFileName: string): Promise<string | null> {
  return await invoke<string | null>("select_project_save_file", {
    default_file_name: defaultFileName,
  });
}

/** Requests the sidecar's `project_open` command (via the Rust
 * `engine_project_open` command) for a `.zerorod` file at `path` (normally
 * a path previously returned by `selectProjectOpenFile`, never a
 * WebView-typed raw string). Throws an `EngineError` (see engine.ts's
 * `isEngineError`) on any structured failure — file not found, permission
 * denied, invalid/corrupt project file, unsupported version, or
 * domain-invalid parameters. */
export async function requestProjectOpen(path: string): Promise<ProjectOpenResult> {
  const result = await invoke<{ schema: string; values: ZeroRodParametersValues }>(
    "engine_project_open",
    { path },
  );
  return { values: result.values };
}

/** Requests the sidecar's `project_save` command (via the Rust
 * `engine_project_save` command) for the given parameter values and
 * destination `path` (either the project's existing current path, or one
 * previously returned by `selectProjectSaveFile`). `values` should always
 * be the caller's `accepted` state, never an uncommitted draft (see
 * docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md "Canonical Save
 * State"). Throws an `EngineError` on any structured failure. */
export async function requestProjectSave(
  values: ZeroRodParametersValues,
  path: string,
): Promise<ProjectSaveResult> {
  const result = await invoke<{ path: string }>("engine_project_save", {
    parameters: buildParametersRequest(values),
    path,
  });
  return { path: result.path };
}
