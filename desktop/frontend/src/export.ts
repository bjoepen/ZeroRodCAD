// Build 024 M1 — export protocol foundation.
//
// Mirrors src/zerorod_sidecar/main.py's `export` command result shape
// exactly (docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md). Like Build
// 023 M1's `requestPreviewMeshWithParameters`, this module only provides
// types and thin invoke() wrappers around the two new Rust commands
// (`select_export_directory`, `engine_export`) — no export UI, no button,
// no status panel. That is M2's job. Proves the WebView-side call shape
// compiles and round-trips correctly against the real commands, nothing
// more.

import { invoke } from "@tauri-apps/api/core";
import { buildParametersRequest, type ZeroRodParametersValues } from "./parameters";

/** One generated output file, as returned by the sidecar's `export`
 * command. `role` is a stable identifier ("body_stl" | "assembly_step" |
 * "report_markdown"), not a filename to parse. */
export interface ExportResultFile {
  role: string;
  filename: string;
  path: string;
}

export interface ExportResult {
  output_directory: string;
  files: ExportResultFile[];
  timing: { export_seconds: number };
}

/** One expected/conflicting output filename, as returned by the sidecar's
 * `export_preflight` command — `role` and `filename` only, never a
 * directory listing. */
export interface ExportPreflightFile {
  role: string;
  filename: string;
}

export interface ExportPreflightResult {
  output_directory: string;
  expected_files: ExportPreflightFile[];
  conflicts: ExportPreflightFile[];
  has_conflicts: boolean;
}

/** Shows the OS's native directory picker via the Rust-owned
 * `select_export_directory` command and returns the chosen path, or `null`
 * if the user cancelled — cancellation is a normal, non-error outcome (see
 * docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md "Dialog cancellation"),
 * never thrown as an EngineError. The WebView never browses or lists a
 * directory itself; this is the only path information it ever receives. */
export async function selectExportDirectory(): Promise<string | null> {
  return await invoke<string | null>("select_export_directory");
}

/** Requests export of the given parameter value set into `outputDirectory`
 * (normally the frontend's `accepted` parameter state — see
 * docs/migration/BUILD-024-HANDOFF.md — and a path previously returned by
 * `selectExportDirectory`, never a WebView-typed raw string) via the Rust
 * `engine_export` command. Existing output files at the destination are
 * overwritten in place (empirically confirmed engine behavior, unchanged by
 * Build 024). Throws an `EngineError` (see engine.ts's `isEngineError`) on
 * any structured failure — invalid parameters, invalid/unwritable
 * destination, or an incomplete write. */
export async function requestExport(
  values: Partial<ZeroRodParametersValues>,
  outputDirectory: string,
): Promise<ExportResult> {
  return await invoke<ExportResult>("engine_export", {
    parameters: buildParametersRequest(values),
    output_directory: outputDirectory,
  });
}

/** Build 024 M2: checks which of `export`'s expected output filenames
 * already exist in `outputDirectory`, without performing an export or
 * granting the WebView any directory-listing capability — the sidecar
 * checks only the fixed, known filename set (see
 * docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md's `project_name`
 * findings) and returns which ones already exist. Same argument shape as
 * `requestExport`; call this first and only call `requestExport` directly
 * (skipping a second preflight) once the caller has its own overwrite
 * confirmation, if any conflicts were reported. Throws an `EngineError` on
 * any structured failure (e.g. invalid destination), same as `requestExport`. */
export async function requestExportPreflight(
  values: Partial<ZeroRodParametersValues>,
  outputDirectory: string,
): Promise<ExportPreflightResult> {
  return await invoke<ExportPreflightResult>("engine_export_preflight", {
    parameters: buildParametersRequest(values),
    output_directory: outputDirectory,
  });
}
