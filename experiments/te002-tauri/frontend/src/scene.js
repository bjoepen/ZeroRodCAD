// TE-002 — minimal Three.js scene: camera, renderer, controls, lights,
// resize handling, camera-fit-to-bounds (sections 19-20).

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export function createScene(container) {
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

  const resize = () => {
    const width = container.clientWidth;
    const height = Math.max(container.clientHeight, 1);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  };
  window.addEventListener("resize", resize);

  function render() {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(render);
  }
  render();

  return { scene, camera, renderer, controls, resize };
}

/**
 * Deterministic "fit camera to bounds" (section 20) — no hard-coded ZeroRod
 * camera angle. Frames the model's bounding box fully in view.
 */
export function fitCameraToBounds(camera, controls, bounds) {
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

export function clearGroup(group) {
  for (const child of [...group.children]) {
    group.remove(child);
    child.geometry?.dispose?.();
    child.material?.dispose?.();
  }
}
