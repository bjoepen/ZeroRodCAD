// TE-002 — zerorod-mesh/v1 -> Three.js conversion (section 19-20).
// Pure data-transformation functions, deliberately separated from
// scene.js/main.js so they're testable without a WebGL context.

import * as THREE from "three";

export const MESH_SCHEMA = "zerorod-mesh/v1";

/**
 * Defensive frontend-side validation mirroring the sidecar's own checks
 * (TE-002 section 13). Returns a list of problem strings; empty = valid.
 * An invalid payload must never reach the renderer.
 */
export function validateMeshPayload(payload) {
  const problems = [];
  if (!payload || typeof payload !== "object") {
    return ["payload must be an object"];
  }
  if (payload.schema !== MESH_SCHEMA) {
    problems.push(`schema must be '${MESH_SCHEMA}', got ${JSON.stringify(payload.schema)}`);
  }
  const meshes = Array.isArray(payload.meshes) ? payload.meshes : [];
  if (meshes.length === 0) {
    problems.push("meshes must be a non-empty array");
  }
  for (const mesh of meshes) {
    const name = mesh?.name ?? "<unnamed>";
    const positions = Array.isArray(mesh?.positions) ? mesh.positions : [];
    const indices = Array.isArray(mesh?.indices) ? mesh.indices : [];
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
    if (indices.some((i) => !Number.isInteger(i) || i < 0 || i >= vertexCount)) {
      problems.push(`mesh '${name}': index out of range [0, ${vertexCount})`);
    }
  }
  const bounds = payload.bounds;
  if (!bounds || !Array.isArray(bounds.min) || !Array.isArray(bounds.max)) {
    problems.push("bounds must have 'min' and 'max'");
  } else {
    for (const key of ["min", "max"]) {
      const value = bounds[key];
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
function indexArrayFor(vertexCount, indices) {
  return vertexCount > 65535 ? new Uint32Array(indices) : new Uint16Array(indices);
}

/**
 * Converts one zerorod-mesh/v1 `meshes[]` entry into a THREE.BufferGeometry.
 * Caller is expected to have already validated the payload.
 */
export function meshEntryToBufferGeometry(meshEntry) {
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
export function lineEntryToBufferGeometry(lineEntry) {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(lineEntry.positions);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  return geometry;
}

/** Converts the full mesh contract payload into ready-to-render geometries. */
export function meshContractToGeometries(payload) {
  const problems = validateMeshPayload(payload);
  if (problems.length > 0) {
    throw new Error(`invalid mesh payload: ${problems.join("; ")}`);
  }
  return {
    meshes: payload.meshes.map((entry) => ({
      name: entry.name,
      geometry: meshEntryToBufferGeometry(entry),
    })),
    lines: payload.lines.map((entry) => ({
      name: entry.name,
      geometry: lineEntryToBufferGeometry(entry),
    })),
    bounds: payload.bounds,
  };
}
