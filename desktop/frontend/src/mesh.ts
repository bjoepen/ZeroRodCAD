// zerorod-mesh/v1 -> Three.js conversion. Pure data-transformation
// functions, deliberately separated from scene.ts/main.ts so they're
// testable without a WebGL context. Adopted from
// experiments/te002-tauri/frontend/src/mesh.js (TE-002) — same validation
// rules, same conversion shape, ported to TypeScript for Build 022 M3.

import * as THREE from "three";

export const MESH_SCHEMA = "zerorod-mesh/v1";

export interface MeshEntry {
  name: string;
  positions: number[];
  indices: number[];
}

export interface LineEntry {
  name: string;
  positions: number[];
}

export interface Bounds {
  min: [number, number, number];
  max: [number, number, number];
}

export interface MeshPayload {
  schema: string;
  meshes: MeshEntry[];
  lines: LineEntry[];
  bounds: Bounds;
}

export interface RenderableMesh {
  name: string;
  geometry: THREE.BufferGeometry;
}

export interface RenderableGeometries {
  meshes: RenderableMesh[];
  lines: RenderableMesh[];
  bounds: Bounds;
}

/**
 * Defensive frontend-side validation mirroring the sidecar's own checks
 * (zerorod_sidecar.mesh_contract.validate_mesh_contract /
 * desktop/src-tauri/src/mesh.rs). Returns a list of problem strings; empty
 * = valid. An invalid payload must never reach the renderer — Rust already
 * validates before this ever arrives, but the frontend does not trust that
 * blindly either, same defense-in-depth TE-002 established.
 */
export function validateMeshPayload(payload: unknown): string[] {
  const problems: string[] = [];
  if (!payload || typeof payload !== "object") {
    return ["payload must be an object"];
  }
  const obj = payload as Record<string, unknown>;
  if (obj.schema !== MESH_SCHEMA) {
    problems.push(`schema must be '${MESH_SCHEMA}', got ${JSON.stringify(obj.schema)}`);
  }
  const meshes = Array.isArray(obj.meshes) ? obj.meshes : [];
  if (meshes.length === 0) {
    problems.push("meshes must be a non-empty array");
  }
  for (const mesh of meshes as Record<string, unknown>[]) {
    const name = typeof mesh?.name === "string" ? mesh.name : "<unnamed>";
    const positions = Array.isArray(mesh?.positions) ? (mesh.positions as unknown[]) : [];
    const indices = Array.isArray(mesh?.indices) ? (mesh.indices as unknown[]) : [];
    if (positions.length === 0) {
      problems.push(`mesh '${name}': positions must be non-empty`);
    } else if (positions.length % 3 !== 0) {
      problems.push(`mesh '${name}': positions length ${positions.length} not a multiple of 3`);
    }
    if (positions.some((v) => typeof v !== "number" || !Number.isFinite(v))) {
      problems.push(`mesh '${name}': positions contain NaN/Inf/non-numeric values`);
    }
    if (indices.length === 0) {
      problems.push(`mesh '${name}': indices must be non-empty`);
    } else if (indices.length % 3 !== 0) {
      problems.push(`mesh '${name}': indices length ${indices.length} not a multiple of 3`);
    }
    const vertexCount = Math.floor(positions.length / 3);
    if (indices.some((i) => !Number.isInteger(i) || (i as number) < 0 || (i as number) >= vertexCount)) {
      problems.push(`mesh '${name}': index out of range [0, ${vertexCount})`);
    }
  }
  const bounds = obj.bounds as Record<string, unknown> | undefined;
  if (!bounds || !Array.isArray(bounds.min) || !Array.isArray(bounds.max)) {
    problems.push("bounds must have 'min' and 'max'");
  } else {
    for (const key of ["min", "max"] as const) {
      const value = bounds[key] as unknown[];
      if (
        !Array.isArray(value) ||
        value.length !== 3 ||
        value.some((v) => typeof v !== "number" || !Number.isFinite(v))
      ) {
        problems.push(`bounds.${key} must be [x, y, z] finite numbers`);
      }
    }
  }
  return problems;
}

/** Picks the smallest typed array that can hold `vertexCount` indices. */
function indexArrayFor(vertexCount: number, indices: number[]): Uint16Array | Uint32Array {
  return vertexCount > 65535 ? new Uint32Array(indices) : new Uint16Array(indices);
}

/**
 * Converts one zerorod-mesh/v1 `meshes[]` entry into a THREE.BufferGeometry.
 * Caller is expected to have already validated the payload.
 */
export function meshEntryToBufferGeometry(meshEntry: MeshEntry): THREE.BufferGeometry {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(meshEntry.positions);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const vertexCount = positions.length / 3;
  geometry.setIndex(new THREE.BufferAttribute(indexArrayFor(vertexCount, meshEntry.indices), 1));
  geometry.computeVertexNormals();
  return geometry;
}

/**
 * Converts one zerorod-mesh/v1 `lines[]` entry (flat [x,y,z,x,y,z,...]
 * position list, consecutive pairs = one segment) into geometry suitable
 * for THREE.LineSegments.
 */
export function lineEntryToBufferGeometry(lineEntry: LineEntry): THREE.BufferGeometry {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(lineEntry.positions);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  return geometry;
}

/** Converts the full mesh contract payload into ready-to-render geometries. */
export function meshContractToGeometries(payload: unknown): RenderableGeometries {
  const problems = validateMeshPayload(payload);
  if (problems.length > 0) {
    throw new Error(`invalid mesh payload: ${problems.join("; ")}`);
  }
  const typed = payload as MeshPayload;
  return {
    meshes: typed.meshes.map((entry) => ({
      name: entry.name,
      geometry: meshEntryToBufferGeometry(entry),
    })),
    lines: typed.lines.map((entry) => ({
      name: entry.name,
      geometry: lineEntryToBufferGeometry(entry),
    })),
    bounds: typed.bounds,
  };
}
