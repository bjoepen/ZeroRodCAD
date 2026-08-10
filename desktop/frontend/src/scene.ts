// Minimal Three.js scene: camera, renderer, controls, lights, resize
// handling, camera-fit-to-bounds. Adopted from
// experiments/te002-tauri/frontend/src/scene.js (TE-002), ported to
// TypeScript for Build 022 M3. No new 3D framework, no shader work, no
// postprocessing — preview infrastructure, not art direction.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { Bounds } from "./mesh";

export interface SceneHandle {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  controls: OrbitControls;
  resize: () => void;
  dispose: () => void;
}

export function createScene(container: HTMLElement): SceneHandle {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1e1e1e);

  const camera = new THREE.PerspectiveCamera(
    50,
    container.clientWidth / Math.max(container.clientHeight, 1),
    0.1,
    10000,
  );

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const directional = new THREE.DirectionalLight(0xffffff, 0.8);
  directional.position.set(1, 1, 1);
  scene.add(directional);

  const resize = (): void => {
    const width = container.clientWidth;
    const height = Math.max(container.clientHeight, 1);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  };
  window.addEventListener("resize", resize);

  let animationFrame = 0;
  let disposed = false;
  function render(): void {
    if (disposed) return;
    controls.update();
    renderer.render(scene, camera);
    animationFrame = requestAnimationFrame(render);
  }
  render();

  const dispose = (): void => {
    disposed = true;
    cancelAnimationFrame(animationFrame);
    window.removeEventListener("resize", resize);
    controls.dispose();
    renderer.dispose();
    if (renderer.domElement.parentNode === container) {
      container.removeChild(renderer.domElement);
    }
  };

  return { scene, camera, renderer, controls, resize, dispose };
}

/**
 * Deterministic "fit camera to bounds" — no hard-coded ZeroRod camera
 * angle. Frames the model's bounding box fully in view.
 */
export function fitCameraToBounds(
  camera: THREE.PerspectiveCamera,
  controls: Pick<OrbitControls, "target" | "update">,
  bounds: Bounds,
): void {
  const min = new THREE.Vector3(...bounds.min);
  const max = new THREE.Vector3(...bounds.max);
  const center = min.clone().add(max).multiplyScalar(0.5);
  const size = max.clone().sub(min);
  const maxDimension = Math.max(size.x, size.y, size.z, 1e-6);

  const fovRadians = (camera.fov * Math.PI) / 180;
  const distance = (maxDimension / 2 / Math.tan(fovRadians / 2)) * 1.6; // margin

  camera.position.set(center.x + distance, center.y + distance * 0.6, center.z + distance);
  camera.near = Math.max(distance / 100, 0.01);
  camera.far = distance * 100;
  camera.updateProjectionMatrix();

  controls.target.copy(center);
  controls.update();
}

/** Build 023 M4 — the camera-refit heuristic for live preview
 * (§29 of the M4 mandate): refitting on every single live update fights the
 * user's own camera/zoom/rotate state, but never refitting risks leaving
 * genuinely new geometry outside the viewable frustum. `EXTREME_BOUNDS_CHANGE_RATIO`
 * (1.5x) means "the model's largest dimension changed by more than 50%" —
 * chosen as a simple, defensible, testable threshold rather than a larger
 * camera-preservation subsystem (the mandate explicitly asks for exactly
 * this level of restraint: "controlled refit/fallback," not a new policy
 * engine). Callers additionally always refit on the very first load of a
 * session, independent of this function. */
export const EXTREME_BOUNDS_CHANGE_RATIO = 1.5;

function boundsMaxDimension(bounds: Bounds): number {
  const min = new THREE.Vector3(...bounds.min);
  const max = new THREE.Vector3(...bounds.max);
  const size = max.clone().sub(min);
  return Math.max(size.x, size.y, size.z, 1e-6);
}

export function isExtremeBoundsChange(
  previous: Bounds,
  next: Bounds,
  ratio: number = EXTREME_BOUNDS_CHANGE_RATIO,
): boolean {
  const previousMax = boundsMaxDimension(previous);
  const nextMax = boundsMaxDimension(next);
  return nextMax / previousMax > ratio || previousMax / nextMax > ratio;
}

/** Removes and disposes every child of `group` — used before adding a fresh
 * preview's geometry, so refresh never accumulates stale scene objects. */
export function clearGroup(group: THREE.Group): void {
  for (const child of [...group.children]) {
    group.remove(child);
    const mesh = child as THREE.Mesh | THREE.LineSegments;
    mesh.geometry?.dispose?.();
    const material = mesh.material;
    if (Array.isArray(material)) {
      material.forEach((m) => m.dispose());
    } else {
      material?.dispose?.();
    }
  }
}
