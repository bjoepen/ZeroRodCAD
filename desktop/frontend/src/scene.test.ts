import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { boundsFromVisibleObjects, fitCameraToBounds, clearGroup, isExtremeBoundsChange } from "./scene";

function boxMesh(name: string, position: [number, number, number]): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1));
  mesh.name = name;
  mesh.position.set(...position);
  return mesh;
}

describe("boundsFromVisibleObjects", () => {
  it("computes bounds from all children when everything is visible", () => {
    const group = new THREE.Group();
    group.add(boxMesh("body", [0, 0, 0]));
    group.add(boxMesh("rod", [10, 0, 0]));

    const bounds = boundsFromVisibleObjects(group)!;
    expect(bounds).not.toBeNull();
    expect(bounds.min[0]).toBeCloseTo(-0.5);
    expect(bounds.max[0]).toBeCloseTo(10.5);
  });

  it("excludes a hidden layer's geometry entirely (§12 of the M3 mandate)", () => {
    const group = new THREE.Group();
    const body = boxMesh("body", [0, 0, 0]);
    const rod = boxMesh("rod", [100, 0, 0]);
    rod.visible = false;
    group.add(body);
    group.add(rod);

    const bounds = boundsFromVisibleObjects(group)!;
    // If the hidden rod's geometry leaked in, max.x would be ~100.5.
    expect(bounds.max[0]).toBeCloseTo(0.5);
  });

  it("returns null when every layer is hidden (safe no-op, not a crash)", () => {
    const group = new THREE.Group();
    const body = boxMesh("body", [0, 0, 0]);
    body.visible = false;
    group.add(body);

    expect(boundsFromVisibleObjects(group)).toBeNull();
  });

  it("returns null for an empty group", () => {
    expect(boundsFromVisibleObjects(new THREE.Group())).toBeNull();
  });

  it("skips a hidden parent group's children even if the children are individually visible", () => {
    const group = new THREE.Group();
    const hiddenSubgroup = new THREE.Group();
    hiddenSubgroup.visible = false;
    hiddenSubgroup.add(boxMesh("strings", [50, 0, 0]));
    group.add(boxMesh("body", [0, 0, 0]));
    group.add(hiddenSubgroup);

    const bounds = boundsFromVisibleObjects(group)!;
    expect(bounds.max[0]).toBeCloseTo(0.5);
  });
});

describe("fitCameraToBounds", () => {
  it("points the camera at the bounds center and updates controls target", () => {
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    const controls = { target: new THREE.Vector3(), update: () => true };
    fitCameraToBounds(camera, controls, { min: [-1, -1, -1], max: [1, 1, 1] });
    expect(controls.target.x).toBeCloseTo(0);
    expect(controls.target.y).toBeCloseTo(0);
    expect(controls.target.z).toBeCloseTo(0);
  });

  it("moves the camera further away for larger bounds", () => {
    const cameraSmall = new THREE.PerspectiveCamera(50, 1, 0.1, 100000);
    const controlsSmall = { target: new THREE.Vector3(), update: () => true };
    fitCameraToBounds(cameraSmall, controlsSmall, { min: [0, 0, 0], max: [1, 1, 1] });
    const distanceSmall = cameraSmall.position.length();

    const cameraLarge = new THREE.PerspectiveCamera(50, 1, 0.1, 100000);
    const controlsLarge = { target: new THREE.Vector3(), update: () => true };
    fitCameraToBounds(cameraLarge, controlsLarge, { min: [0, 0, 0], max: [100, 100, 100] });
    const distanceLarge = cameraLarge.position.length();

    expect(distanceLarge).toBeGreaterThan(distanceSmall);
  });

  it("does not throw on a degenerate (zero-size) bounds box", () => {
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    const controls = { target: new THREE.Vector3(), update: () => true };
    expect(() =>
      fitCameraToBounds(camera, controls, { min: [0, 0, 0], max: [0, 0, 0] }),
    ).not.toThrow();
  });
});

describe("clearGroup", () => {
  it("removes all children and disposes their geometry/material", () => {
    const group = new THREE.Group();
    const geometry = new THREE.BoxGeometry();
    const material = new THREE.MeshStandardMaterial();
    const mesh = new THREE.Mesh(geometry, material);
    group.add(mesh);

    let geometryDisposed = false;
    let materialDisposed = false;
    geometry.dispose = () => {
      geometryDisposed = true;
    };
    material.dispose = () => {
      materialDisposed = true;
    };

    clearGroup(group);

    expect(group.children).toHaveLength(0);
    expect(geometryDisposed).toBe(true);
    expect(materialDisposed).toBe(true);
  });

  it("does not throw on an already-empty group", () => {
    const group = new THREE.Group();
    expect(() => clearGroup(group)).not.toThrow();
  });

  it("disposes every material in a multi-material mesh", () => {
    const group = new THREE.Group();
    const materials = [new THREE.MeshStandardMaterial(), new THREE.MeshStandardMaterial()];
    const disposed = [false, false];
    materials[0].dispose = () => {
      disposed[0] = true;
    };
    materials[1].dispose = () => {
      disposed[1] = true;
    };
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(), materials);
    group.add(mesh);

    clearGroup(group);

    expect(disposed).toEqual([true, true]);
  });
});

describe("isExtremeBoundsChange", () => {
  const base = { min: [0, 0, 0] as [number, number, number], max: [10, 10, 10] as [number, number, number] };

  it("is false for an unchanged bounds box", () => {
    expect(isExtremeBoundsChange(base, base)).toBe(false);
  });

  it("is false for a small (< default ratio) size change", () => {
    const next = { min: [0, 0, 0] as [number, number, number], max: [12, 10, 10] as [number, number, number] };
    expect(isExtremeBoundsChange(base, next)).toBe(false);
  });

  it("is true when the model grows past the default ratio", () => {
    const next = { min: [0, 0, 0] as [number, number, number], max: [20, 10, 10] as [number, number, number] };
    expect(isExtremeBoundsChange(base, next)).toBe(true);
  });

  it("is true when the model shrinks past the default ratio", () => {
    const next = { min: [0, 0, 0] as [number, number, number], max: [5, 5, 5] as [number, number, number] };
    expect(isExtremeBoundsChange(base, next)).toBe(true);
  });

  it("respects a custom ratio", () => {
    const next = { min: [0, 0, 0] as [number, number, number], max: [12, 10, 10] as [number, number, number] };
    expect(isExtremeBoundsChange(base, next, 1.1)).toBe(true);
    expect(isExtremeBoundsChange(base, next, 5)).toBe(false);
  });
});
