// TE-002 — wiring: Load ZeroRod button -> sidecar -> mesh contract ->
// Three.js scene (sections 16, 19, 22).

import * as THREE from "three";
import { createScene, fitCameraToBounds, clearGroup } from "./scene.js";
import { meshContractToGeometries } from "./mesh.js";
import { requestPreview, SidecarTimeoutError, SidecarProcessError } from "./sidecar.js";

const statusEl = document.getElementById("status");
const loadButton = document.getElementById("load-button");
const viewport = document.getElementById("viewport");

function setStatus(state, text) {
  statusEl.dataset.state = state;
  statusEl.textContent = text;
}

const { scene, camera, controls } = createScene(viewport);
const modelGroup = new THREE.Group();
scene.add(modelGroup);

const meshMaterial = new THREE.MeshStandardMaterial({ color: 0x8a8f98, metalness: 0.1, roughness: 0.7 });
const lineMaterial = new THREE.LineBasicMaterial({ color: 0xffb454 });

async function loadZeroRod() {
  loadButton.disabled = true;
  setStatus("loading", "Loading...");
  try {
    const started = performance.now();
    const result = await requestPreview();
    const roundTripMs = performance.now() - started;

    const geometryStarted = performance.now();
    const { meshes, lines, bounds } = meshContractToGeometries(result);
    clearGroup(modelGroup);
    for (const { geometry } of meshes) {
      modelGroup.add(new THREE.Mesh(geometry, meshMaterial));
    }
    for (const { geometry } of lines) {
      modelGroup.add(new THREE.LineSegments(geometry, lineMaterial));
    }
    fitCameraToBounds(camera, controls, bounds);
    const geometryMs = performance.now() - geometryStarted;

    const vertexCount = meshes.reduce((sum, m) => sum + m.geometry.attributes.position.count, 0);
    const triangleCount = meshes.reduce(
      (sum, m) => sum + m.geometry.index.count / 3,
      0,
    );
    setStatus(
      "ready",
      `Ready — ${vertexCount} vertices, ${triangleCount} triangles ` +
        `(roundtrip ${roundTripMs.toFixed(0)}ms, geometry ${geometryMs.toFixed(1)}ms)`,
    );
  } catch (error) {
    if (error instanceof SidecarTimeoutError) {
      setStatus("error", `Timeout: ${error.message}`);
    } else if (error instanceof SidecarProcessError) {
      setStatus("error", `Sidecar error: ${error.message}`);
    } else if (error?.message?.startsWith("invalid mesh payload")) {
      setStatus("error", `Invalid mesh: ${error.message}`);
    } else {
      setStatus("error", `Unexpected error: ${error}`);
    }
  } finally {
    loadButton.disabled = false;
  }
}

loadButton.addEventListener("click", loadZeroRod);
