// Build 022 M3 — the Three.js preview component boundary. Owns everything
// GPU/scene-related: initializing the renderer, receiving the mesh payload,
// validating it, building geometry, replacing old scene objects, fitting
// the camera, resizing, and disposing geometry/materials/renderer. main.ts
// only wires this to a button and a status callback — no Three.js code
// lives in main.ts itself.

import * as THREE from "three";
import { isEngineError, requestPreviewMesh } from "./engine";
import { meshContractToGeometries, type RenderableMesh } from "./mesh";
import { clearGroup, createScene, fitCameraToBounds, type SceneHandle } from "./scene";
import type { StatusValue } from "./status";

export type PreviewState = "idle" | "loading" | "ready" | "error";

export type PreviewStateListener = (state: PreviewState, detail: string) => void;

/** Pure — maps a preview lifecycle state to the same StatusValue vocabulary
 * the rest of the status panel uses, so main.ts doesn't need its own copy. */
export function previewStateToStatusValue(state: PreviewState): StatusValue {
  const mapping: Record<PreviewState, StatusValue> = {
    idle: "NOT_READY",
    loading: "RUNNING",
    ready: "READY",
    error: "ERROR",
  };
  return mapping[state];
}

export interface RenderSummary {
  vertexCount: number;
  triangleCount: number;
  lineCount: number;
}

/** Pure — counts vertices/triangles/lines across already-built geometries.
 * Separated from `load()` so it's testable without a WebGL context. */
export function summarizeRenderResult(
  meshes: RenderableMesh[],
  lines: RenderableMesh[],
): RenderSummary {
  const vertexCount = meshes.reduce(
    (sum, m) => sum + (m.geometry.attributes.position?.count ?? 0),
    0,
  );
  const triangleCount = meshes.reduce(
    (sum, m) => sum + (m.geometry.index ? m.geometry.index.count / 3 : 0),
    0,
  );
  return { vertexCount, triangleCount, lineCount: lines.length };
}

/** Pure — formats the "Ready — ..." status text from a render summary and
 * timing. Separated so the exact wording is testable without a renderer. */
export function formatReadyDetail(
  summary: RenderSummary,
  roundTripMs: number,
  geometryMs: number,
): string {
  return (
    `Ready — ${summary.vertexCount} vertices, ${summary.triangleCount} triangles, ` +
    `${summary.lineCount} line(s) (roundtrip ${roundTripMs.toFixed(0)}ms, geometry ${geometryMs.toFixed(1)}ms)`
  );
}

/** Pure — formats the error detail from a thrown value, same classification
 * every other engine-facing UI handler in main.ts uses. */
export function formatErrorDetail(error: unknown): string {
  if (isEngineError(error)) {
    return `${error.code}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export interface PreviewController {
  /** Requests a real ZeroRod preview mesh and renders it. Replaces any
   * previously rendered model — never accumulates stale geometry. */
  load: () => Promise<void>;
  /** Releases the renderer, controls, geometry, and materials. Call once,
   * when the preview is being torn down (e.g. page/app unload). */
  dispose: () => void;
}

export function createPreviewController(
  container: HTMLElement,
  onStateChange: PreviewStateListener,
): PreviewController {
  const sceneHandle: SceneHandle = createScene(container);
  const { scene, camera, controls, resize, dispose: disposeScene } = sceneHandle;

  const modelGroup = new THREE.Group();
  scene.add(modelGroup);

  const meshMaterial = new THREE.MeshStandardMaterial({
    color: 0x8a8f98,
    metalness: 0.1,
    roughness: 0.7,
  });
  const lineMaterial = new THREE.LineBasicMaterial({ color: 0xffb454 });

  // Correct initial size once the container has real dimensions in the DOM
  // (createScene's own constructor-time measurement can race layout).
  resize();

  async function load(): Promise<void> {
    onStateChange("loading", "Loading…");
    try {
      const started = performance.now();
      const payload = await requestPreviewMesh();
      const roundTripMs = performance.now() - started;

      const geometryStarted = performance.now();
      const { meshes, lines, bounds } = meshContractToGeometries(payload);

      // Refresh must not accumulate stale geometry from a prior load.
      clearGroup(modelGroup);
      for (const { geometry } of meshes) {
        modelGroup.add(new THREE.Mesh(geometry, meshMaterial));
      }
      for (const { geometry } of lines) {
        modelGroup.add(new THREE.LineSegments(geometry, lineMaterial));
      }
      fitCameraToBounds(camera, controls, bounds);
      const geometryMs = performance.now() - geometryStarted;

      const summary = summarizeRenderResult(meshes, lines);
      onStateChange("ready", formatReadyDetail(summary, roundTripMs, geometryMs));
    } catch (error) {
      onStateChange("error", formatErrorDetail(error));
    }
  }

  function dispose(): void {
    clearGroup(modelGroup);
    meshMaterial.dispose();
    lineMaterial.dispose();
    disposeScene();
  }

  return { load, dispose };
}
