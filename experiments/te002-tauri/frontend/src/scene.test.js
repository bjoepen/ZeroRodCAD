import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { fitCameraToBounds } from "./scene.js";

describe("fitCameraToBounds", () => {
  it("points the camera at the bounds center and updates controls target", () => {
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    const controls = { target: new THREE.Vector3(), update: () => {} };
    fitCameraToBounds(camera, controls, { min: [-1, -1, -1], max: [1, 1, 1] });
    expect(controls.target.x).toBeCloseTo(0);
    expect(controls.target.y).toBeCloseTo(0);
    expect(controls.target.z).toBeCloseTo(0);
  });

  it("moves the camera further away for larger bounds", () => {
    const cameraSmall = new THREE.PerspectiveCamera(50, 1, 0.1, 100000);
    const controlsSmall = { target: new THREE.Vector3(), update: () => {} };
    fitCameraToBounds(cameraSmall, controlsSmall, { min: [0, 0, 0], max: [1, 1, 1] });
    const distanceSmall = cameraSmall.position.length();

    const cameraLarge = new THREE.PerspectiveCamera(50, 1, 0.1, 100000);
    const controlsLarge = { target: new THREE.Vector3(), update: () => {} };
    fitCameraToBounds(cameraLarge, controlsLarge, { min: [0, 0, 0], max: [100, 100, 100] });
    const distanceLarge = cameraLarge.position.length();

    expect(distanceLarge).toBeGreaterThan(distanceSmall);
  });

  it("does not throw on a degenerate (zero-size) bounds box", () => {
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    const controls = { target: new THREE.Vector3(), update: () => {} };
    expect(() => fitCameraToBounds(camera, controls, { min: [0, 0, 0], max: [0, 0, 0] })).not.toThrow();
  });
});
