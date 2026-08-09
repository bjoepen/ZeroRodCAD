import { describe, expect, it } from "vitest";
import * as THREE from "three";
import {
  MESH_SCHEMA,
  validateMeshPayload,
  meshEntryToBufferGeometry,
  lineEntryToBufferGeometry,
  meshContractToGeometries,
  type MeshPayload,
} from "./mesh";

function validPayload(): MeshPayload {
  return {
    schema: MESH_SCHEMA,
    meshes: [
      {
        name: "tri",
        positions: [0, 0, 0, 1, 0, 0, 0, 1, 0],
        indices: [0, 1, 2],
      },
    ],
    lines: [{ name: "edge", positions: [0, 0, 0, 1, 1, 1] }],
    bounds: { min: [0, 0, 0], max: [1, 1, 1] },
  };
}

describe("validateMeshPayload", () => {
  it("accepts a valid payload", () => {
    expect(validateMeshPayload(validPayload())).toEqual([]);
  });

  it("rejects wrong schema", () => {
    const payload = validPayload();
    payload.schema = "wrong";
    expect(validateMeshPayload(payload).length).toBeGreaterThan(0);
  });

  it("rejects empty meshes", () => {
    const payload = validPayload();
    payload.meshes = [];
    expect(validateMeshPayload(payload).some((p) => p.includes("non-empty"))).toBe(true);
  });

  it("rejects positions not a multiple of 3", () => {
    const payload = validPayload();
    payload.meshes[0].positions = [0, 0];
    const problems = validateMeshPayload(payload);
    expect(problems.some((p) => p.includes("multiple of 3") && p.includes("positions"))).toBe(true);
  });

  it("rejects indices not a multiple of 3", () => {
    const payload = validPayload();
    payload.meshes[0].indices = [0, 1];
    const problems = validateMeshPayload(payload);
    expect(problems.some((p) => p.includes("multiple of 3") && p.includes("indices"))).toBe(true);
  });

  it("rejects out-of-range indices", () => {
    const payload = validPayload();
    payload.meshes[0].indices = [0, 1, 5];
    const problems = validateMeshPayload(payload);
    expect(problems.some((p) => p.includes("out of range"))).toBe(true);
  });

  it("rejects NaN/Infinity positions", () => {
    const payload = validPayload();
    payload.meshes[0].positions = [NaN, 0, 0, 1, 0, 0, 0, 1, 0];
    const problems = validateMeshPayload(payload);
    expect(problems.some((p) => p.includes("NaN"))).toBe(true);

    const payload2 = validPayload();
    payload2.meshes[0].positions = [Infinity, 0, 0, 1, 0, 0, 0, 1, 0];
    expect(validateMeshPayload(payload2).some((p) => p.includes("NaN") || p.includes("Inf"))).toBe(true);
  });

  it("rejects missing bounds", () => {
    const payload = validPayload();
    // @ts-expect-error deliberately invalid for the test
    delete payload.bounds;
    expect(validateMeshPayload(payload).some((p) => p.includes("bounds"))).toBe(true);
  });

  it("handles a completely empty object gracefully (no throw)", () => {
    expect(() => validateMeshPayload({})).not.toThrow();
    expect(validateMeshPayload({}).length).toBeGreaterThan(0);
  });

  it("handles null/undefined payload without throwing", () => {
    expect(validateMeshPayload(null)).toEqual(["payload must be an object"]);
    expect(validateMeshPayload(undefined)).toEqual(["payload must be an object"]);
  });
});

describe("meshEntryToBufferGeometry", () => {
  it("builds a BufferGeometry with position and index attributes", () => {
    const geometry = meshEntryToBufferGeometry(validPayload().meshes[0]);
    expect(geometry).toBeInstanceOf(THREE.BufferGeometry);
    expect(geometry.attributes.position.count).toBe(3);
    expect(geometry.index!.count).toBe(3);
  });

  it("computes vertex normals", () => {
    const geometry = meshEntryToBufferGeometry(validPayload().meshes[0]);
    expect(geometry.attributes.normal).toBeDefined();
  });

  it("uses Uint32Array indices for large vertex counts", () => {
    const bigMesh = {
      name: "big",
      positions: new Array(70000 * 3).fill(0),
      indices: [0, 1, 2],
    };
    const geometry = meshEntryToBufferGeometry(bigMesh);
    expect(geometry.index!.array).toBeInstanceOf(Uint32Array);
  });

  it("uses Uint16Array indices for small vertex counts", () => {
    const geometry = meshEntryToBufferGeometry(validPayload().meshes[0]);
    expect(geometry.index!.array).toBeInstanceOf(Uint16Array);
  });
});

describe("lineEntryToBufferGeometry", () => {
  it("builds line geometry from flat positions", () => {
    const geometry = lineEntryToBufferGeometry(validPayload().lines[0]);
    expect(geometry.attributes.position.count).toBe(2);
  });
});

describe("meshContractToGeometries", () => {
  it("converts a full valid payload", () => {
    const { meshes, lines, bounds } = meshContractToGeometries(validPayload());
    expect(meshes).toHaveLength(1);
    expect(meshes[0].name).toBe("tri");
    expect(lines).toHaveLength(1);
    expect(bounds).toEqual({ min: [0, 0, 0], max: [1, 1, 1] });
  });

  it("throws (does not silently render) on an invalid payload", () => {
    const payload = validPayload();
    payload.meshes[0].indices = [0, 1, 99];
    expect(() => meshContractToGeometries(payload)).toThrow(/invalid mesh payload/);
  });

  it("handles an empty-meshes payload by throwing, never crashing the renderer", () => {
    const payload = validPayload();
    payload.meshes = [];
    expect(() => meshContractToGeometries(payload)).toThrow();
  });
});
