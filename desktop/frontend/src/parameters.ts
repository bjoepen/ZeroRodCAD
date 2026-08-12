// zerorod-parameters/v1 — TypeScript foundation for Build 023 M1.
//
// Mirrors src/zerorodcad/parameters.py's ZeroRodParameters field shape
// (docs/contracts/ZEROROD-PARAMETERS-V1.md) exactly — same field names,
// same units. This module only provides types, a request builder, and
// basic structural/type shape validation (mirroring the sidecar's own
// Level 1/2 checks in zerorod_sidecar/parameters_contract.py). It does NOT
// reimplement cross-parameter/domain rules (Level 3, e.g. "groove diameter
// must be smaller than rod diameter") — those stay engine-near in
// zerorodcad.validation, per the single-source-of-truth mandate. No UI
// controls are built here (Build 023 M1 is contract foundation only).

import { invoke } from "@tauri-apps/api/core";

export const PARAMETERS_SCHEMA = "zerorod-parameters/v1";

/** Mirrors ZeroRodParameters.to_dict()'s shape exactly — same field names,
 * same units (all millimeters except string_gauges_inch, which is inches —
 * see docs/contracts/ZEROROD-PARAMETERS-V1.md's Unit Note). */
export interface ZeroRodParametersValues {
  project_name: string;
  body_width: number;
  body_depth: number;
  fretboard_height: number;
  rod_diameter: number;
  groove_diameter: number;
  rod_center_z_offset: number;
  groove_front_clearance: number;
  string_gauges_inch: number[];
  string_spacing: number;
  string_inlet_y: number;
  string_inlet_z: number;
  channel_diameter: number;
  channel_overrun_at_inlet: number;
  channel_rod_clearance: number;
  minimum_wall: number;
}

export interface ParametersRequest {
  schema: typeof PARAMETERS_SCHEMA;
  values: Partial<ZeroRodParametersValues>;
}

const NUMERIC_FIELDS: readonly (keyof ZeroRodParametersValues)[] = [
  "body_width",
  "body_depth",
  "fretboard_height",
  "rod_diameter",
  "groove_diameter",
  "rod_center_z_offset",
  "groove_front_clearance",
  "string_spacing",
  "string_inlet_y",
  "string_inlet_z",
  "channel_diameter",
  "channel_overrun_at_inlet",
  "channel_rod_clearance",
  "minimum_wall",
];

/** Wraps a (possibly partial) value set in the zerorod-parameters/v1
 * envelope. Omitted fields fall back to the engine's own dataclass
 * defaults on the Python side — this function does not fill them in. */
export function buildParametersRequest(
  values: Partial<ZeroRodParametersValues>,
): ParametersRequest {
  return { schema: PARAMETERS_SCHEMA, values };
}

/**
 * Structural/type shape validation only — mirrors
 * zerorod_sidecar.parameters_contract's Level 1/2 checks so a client can
 * reject an obviously malformed value set before sending it. Deliberately
 * does NOT validate ranges or cross-parameter rules (Level 3); those are
 * engine-owned and can only be authoritatively checked by
 * zerorodcad.validation.validate_parameters. Returns a list of problem
 * strings; empty = structurally valid.
 */
export function validateParametersShape(values: unknown): string[] {
  const problems: string[] = [];
  if (!values || typeof values !== "object" || Array.isArray(values)) {
    return ["values must be an object"];
  }
  const obj = values as Record<string, unknown>;

  if ("project_name" in obj && typeof obj.project_name !== "string") {
    problems.push("project_name must be a string");
  }

  for (const field of NUMERIC_FIELDS) {
    if (field in obj && typeof obj[field] !== "number") {
      problems.push(`${field} must be a number`);
    }
  }

  if ("string_gauges_inch" in obj) {
    const gauges = obj.string_gauges_inch;
    if (!Array.isArray(gauges) || !gauges.every((g) => typeof g === "number")) {
      problems.push("string_gauges_inch must be an array of numbers");
    }
  }

  return problems;
}

/** Build 023 M1 protocol foundation: fetches the single authoritative
 * default parameter set from the sidecar (via the Rust
 * `engine_parameters_defaults` command) instead of hardcoding a second copy
 * in TypeScript (docs/contracts/ZEROROD-PARAMETERS-V1.md). Not called from
 * any UI in M1. */
export async function fetchDefaultParameters(): Promise<ZeroRodParametersValues> {
  const result = await invoke<{ schema: string; values: ZeroRodParametersValues }>(
    "engine_parameters_defaults",
  );
  return result.values;
}

/** Build 023 M1 protocol foundation: requests a ZeroRod preview mesh for an
 * explicit parameter value set (via the Rust
 * `engine_preview_mesh_with_parameters` command). Returns the raw
 * zerorod-mesh/v1 payload — callers pass it through
 * `meshContractToGeometries` (mesh.ts) exactly like the existing
 * parameterless preview path. Not called from any UI in M1. */
export async function requestPreviewMeshWithParameters(
  values: Partial<ZeroRodParametersValues>,
): Promise<unknown> {
  return await invoke("engine_preview_mesh_with_parameters", {
    parameters: buildParametersRequest(values),
  });
}
