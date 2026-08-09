import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { fitCameraToBounds, clearGroup } from "./scene";

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
