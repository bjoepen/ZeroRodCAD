// Build 022 M3 — the Three.js preview component boundary. Owns everything
// GPU/scene-related: initializing the renderer, receiving the mesh payload,
// validating it, building geometry, replacing old scene objects, fitting
// the camera, resizing, and disposing geometry/materials/renderer. main.ts
// only wires this to a button and a status callback — no Three.js code
// lives in main.ts itself.
//
// Build 023 M3 extended `load()` with an optional `values` argument so the
// same geometry-replacement path serves both the parameterless "Load /
// Refresh ZeroRod" button and the parameter panel's Apply flow.
//
// Build 023 M4 splits that path into two exported halves —
// `fetchPreview()` (network/IPC round trip + mesh validation/conversion,
// no scene mutation) and `commitPreview()` (synchronous scene replacement)
// — so parameter_panel.ts's live-preview scheduler (live_preview.ts) can
// fetch a result, check it's still the latest desired generation, and only
// *then* commit it to the visible scene. A stale fetch is therefore never
// even offered to `commitPreview` — the generation gate lives above this
// module, but this module is what makes gating possible without a second
// renderer or a duplicated fetch/convert implementation. `load()` remains
// exactly what it was (fetch immediately followed by an unconditional
// commit) for the manual "Load / Refresh ZeroRod" button, which has no
// generation concept to gate against.
//
// M4 also changes camera behavior: refitting on every single update fights
// a user who has manually framed a detail (§29 of the M4 mandate).
// `commitPreview` now only refits on the very first commit of the session
// and on an "extreme" bounds change (`scene.ts`'s `isExtremeBoundsChange`)
// — not unconditionally. This applies uniformly to the manual button, the
// live-preview path, and Apply, since all three now share this one commit
// function (§2 of the M4 mandate: one pipeline).

import * as THREE from "three";
import { isEngineError, requestPreviewMesh } from "./engine";
import { meshContractToGeometries, type Bounds, type RenderableMesh } from "./mesh";
import { requestPreviewMeshWithParameters, type ZeroRodParametersValues } from "./parameters";
import { clearGroup, createScene, fitCameraToBounds, isExtremeBoundsChange, type SceneHandle } from "./scene";
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

/** Build 023 M4 — the fetched-but-not-yet-committed result of a preview
 * request: everything `commitPreview` needs, and nothing that touches the
 * scene yet. */
export interface ParsedPreviewData {
  meshes: RenderableMesh[];
  lines: RenderableMesh[];
  bounds: Bounds;
  roundTripMs: number;
  geometryParseMs: number;
}

export type FetchPreviewResult =
  | { ok: true; data: ParsedPreviewData }
  | { ok: false; error: unknown };

export interface PreviewController {
  /** Requests a real ZeroRod preview mesh and renders it, replacing any
   * previously rendered model — never accumulates stale geometry. With no
   * argument, requests the engine's canonical defaults. With `values`,
   * requests that explicit zerorod-parameters/v1 value set instead. Fetches
   * and commits unconditionally (no generation gate) — used by the manual
   * "Load / Refresh ZeroRod" button, which has no live-preview scheduler
   * behind it. */
  load: (values?: Partial<ZeroRodParametersValues>) => Promise<PreviewLoadResult>;
  /** Build 023 M4 — the network/IPC half only: requests the mesh and
   * validates/converts it, but never touches the scene. Callers that need
   * generation-gated commit (the live-preview scheduler) use this plus
   * `commitPreview` instead of `load`. */
  fetchPreview: (values?: Partial<ZeroRodParametersValues>) => Promise<FetchPreviewResult>;
  /** Build 023 M4 — the scene-mutation half only: replaces the modelGroup's
   * geometry with `data`, disposing the old geometry first, and refits the
   * camera only on the first-ever commit or an extreme bounds change (see
   * this module's doc comment and `scene.ts`'s `isExtremeBoundsChange`).
   * Also updates the status callback exactly like `load` does. */
  commitPreview: (data: ParsedPreviewData) => void;
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

  let hasCommittedOnce = false;
  let lastBounds: Bounds | null = null;

  async function fetchPreview(values?: Partial<ZeroRodParametersValues>): Promise<FetchPreviewResult> {
    try {
      const started = performance.now();
      const payload = values
        ? await requestPreviewMeshWithParameters(values)
        : await requestPreviewMesh();
      const roundTripMs = performance.now() - started;

      const geometryStarted = performance.now();
      const { meshes, lines, bounds } = meshContractToGeometries(payload);
      const geometryParseMs = performance.now() - geometryStarted;

      return { ok: true, data: { meshes, lines, bounds, roundTripMs, geometryParseMs } };
    } catch (error) {
      return { ok: false, error };
    }
  }

  function commitPreview(data: ParsedPreviewData): void {
    // Refresh must not accumulate stale geometry from a prior commit.
    clearGroup(modelGroup);
    for (const { geometry } of data.meshes) {
      modelGroup.add(new THREE.Mesh(geometry, meshMaterial));
    }
    for (const { geometry } of data.lines) {
      modelGroup.add(new THREE.LineSegments(geometry, lineMaterial));
    }

    const shouldRefit =
      !hasCommittedOnce || (lastBounds !== null && isExtremeBoundsChange(lastBounds, data.bounds));
    if (shouldRefit) {
      fitCameraToBounds(camera, controls, data.bounds);
    }
    hasCommittedOnce = true;
    lastBounds = data.bounds;

    const summary = summarizeRenderResult(data.meshes, data.lines);
    onStateChange("ready", formatReadyDetail(summary, data.roundTripMs, data.geometryParseMs));
  }

  async function load(values?: Partial<ZeroRodParametersValues>): Promise<PreviewLoadResult> {
    onStateChange("loading", "Loading…");
    const result = await fetchPreview(values);
    if (!result.ok) {
      onStateChange("error", formatErrorDetail(result.error));
      return { ok: false, error: result.error };
    }
    commitPreview(result.data);
    return { ok: true };
  }

  function dispose(): void {
    clearGroup(modelGroup);
    meshMaterial.dispose();
    lineMaterial.dispose();
    disposeScene();
  }

  return { load, fetchPreview, commitPreview, dispose };
}
