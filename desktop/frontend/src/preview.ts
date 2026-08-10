// Build 022 M3 — the Three.js preview component boundary. Owns everything
// GPU/scene-related: initializing the renderer, receiving the mesh payload,
// validating it, building geometry, replacing old scene objects, fitting
// the camera, resizing, and disposing geometry/materials/renderer. main.ts
// only wires this to a button and a status callback — no Three.js code
// lives in main.ts itself.
//
// Build 023 M3 extends `load()` with an optional `values` argument so the
// same geometry-replacement path serves both the parameterless "Load /
// Refresh ZeroRod" button (unchanged since M2/M3) and the parameter panel's
// Apply flow — no second Three.js scene, no re-initialized renderer per
// Apply (§20 of the M3 mandate). The existing fetch → validate → convert →
// *then* clear/replace ordering already made a failed request leave the old
// geometry untouched (§18/§21's "atomic preview replacement" requirement) —
// M3 does not need to change that ordering, only add a second data source.

import * as THREE from "three";
import { isEngineError, requestPreviewMesh } from "./engine";
import { meshContractToGeometries, type RenderableMesh } from "./mesh";
import { requestPreviewMeshWithParameters, type ZeroRodParametersValues } from "./parameters";
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

/** Build 023 M3 — lets a caller (parameter_panel.ts's Apply handler) react
 * to success/failure without duplicating error formatting; `onStateChange`
 * remains the single place that updates the visible status text. */
export interface PreviewLoadResult {
  ok: boolean;
  error?: unknown;
}

export interface PreviewController {
  /** Requests a real ZeroRod preview mesh and renders it, replacing any
   * previously rendered model — never accumulates stale geometry. With no
   * argument, requests the engine's canonical defaults (unchanged since
   * M2/M3). With `values`, requests that explicit zerorod-parameters/v1
   * value set instead (Build 023 M3's Apply path) — same rendering code,
   * same atomicity guarantee: a failed request never touches the currently
   * displayed geometry. */
  load: (values?: Partial<ZeroRodParametersValues>) => Promise<PreviewLoadResult>;
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

  async function load(values?: Partial<ZeroRodParametersValues>): Promise<PreviewLoadResult> {
    onStateChange("loading", "Loading…");
    try {
      const started = performance.now();
      const payload = values
        ? await requestPreviewMeshWithParameters(values)
        : await requestPreviewMesh();
      const roundTripMs = performance.now() - started;

      const geometryStarted = performance.now();
      const { meshes, lines, bounds } = meshContractToGeometries(payload);

      // Refresh must not accumulate stale geometry from a prior load. This
      // only runs after the fetch and mesh conversion above have already
      // succeeded, so a failed/invalid request never reaches this point —
      // the previously displayed geometry is left completely untouched.
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
      return { ok: true };
    } catch (error) {
      onStateChange("error", formatErrorDetail(error));
      return { ok: false, error };
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
