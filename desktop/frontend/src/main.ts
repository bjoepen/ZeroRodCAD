import "./style.css";
import { fetchAppInfo } from "./app_info";
import {
  fetchEngineStatus,
  fetchSidecarStatus,
  isEngineError,
  pingEngine,
  requestPreviewSummary,
  type LifecycleState,
} from "./engine";
import { createParameterPanelController } from "./parameter_panel";
import { createPreviewController, previewStateToStatusValue, type PreviewState } from "./preview";
import { renderStatusRows, type StatusRow, type StatusValue } from "./status";

const appEl = document.querySelector<HTMLDivElement>("#app")!;

// The DOM shell is built exactly once (below, in init()). Only the status
// panel and the last-action text update afterward — never the whole #app
// innerHTML — because the viewport div holds a live Three.js canvas that a
// full re-render would tear down and silently orphan on every status change.
appEl.innerHTML = `
  <main class="foundation">
    <h1>ZeroRodCAD Desktop 2.0</h1>
    <p class="subtitle">Build 023 — Milestone 4: Live Preview Behavior & UX</p>
    <div class="layout">
      <section class="sidebar">
        <section class="status-panel" id="status-panel"></section>
        <section class="actions">
          <button id="start-check-engine" type="button">Start / Check Engine</button>
          <button id="ping-engine" type="button">Ping Engine</button>
          <button id="request-preview" type="button">Request Preview Data</button>
          <button id="load-zerorod" type="button">Load / Refresh ZeroRod</button>
        </section>
        <pre id="last-action" class="last-action"></pre>
      </section>
      <section class="parameters" id="parameter-panel"></section>
      <section class="viewport" id="viewport"></section>
    </div>
  </main>
`;

const statusPanelEl = document.querySelector<HTMLDivElement>("#status-panel")!;
const lastActionEl = document.querySelector<HTMLPreElement>("#last-action")!;
const viewportEl = document.querySelector<HTMLDivElement>("#viewport")!;
const parameterPanelEl = document.querySelector<HTMLDivElement>("#parameter-panel")!;

const rows: StatusRow[] = [
  { id: "shell", label: "Desktop shell", value: "READY" },
  { id: "rust-bridge", label: "Rust bridge", value: "NOT_READY" },
  { id: "python-sidecar", label: "Python sidecar", value: "STOPPED" },
  { id: "cad-engine", label: "CAD engine", value: "NOT_READY" },
  { id: "3d-preview", label: "3D preview", value: "NOT_READY" },
];

function lifecycleToStatusValue(state: LifecycleState): StatusValue {
  return state; // StatusValue is a superset of LifecycleState
}

function renderStatusPanel(): void {
  statusPanelEl.innerHTML = renderStatusRows(rows);
}

function setRow(id: string, value: StatusValue, detail?: string): void {
  const index = rows.findIndex((row) => row.id === id);
  if (index !== -1) {
    rows[index] = { id, label: rows[index].label, value, detail };
  }
  renderStatusPanel();
}

function setLastAction(text: string): void {
  lastActionEl.textContent = text;
}

async function timed<T>(action: () => Promise<T>): Promise<{ result: T; ms: number }> {
  const started = performance.now();
  const result = await action();
  return { result, ms: performance.now() - started };
}

async function handleStartCheckEngine(): Promise<void> {
  try {
    const { result: ping, ms } = await timed(pingEngine);
    const status = await fetchEngineStatus();
    setRow("python-sidecar", lifecycleToStatusValue(status.state), `pid ${ping.pid} · ${ms.toFixed(0)} ms`);
    setLastAction(`Start / Check Engine: ok (pid ${ping.pid}, ${ms.toFixed(0)} ms)`);
  } catch (error) {
    setRow("python-sidecar", "ERROR", isEngineError(error) ? error.code : String(error));
    setLastAction(
      `Start / Check Engine failed: ${isEngineError(error) ? `${error.code}: ${error.message}` : String(error)}`,
    );
  }
}

async function handlePingEngine(): Promise<void> {
  try {
    const { result: sidecarStatus, ms } = await timed(fetchSidecarStatus);
    setRow(
      "cad-engine",
      "CONNECTED",
      `${sidecarStatus.cadquery_version ?? "?"} / ${sidecarStatus.ocp_variant ?? "?"} · vtk=${sidecarStatus.vtk_installed} · ${ms.toFixed(0)} ms`,
    );
    setLastAction(`Ping Engine: ${JSON.stringify(sidecarStatus)} (${ms.toFixed(0)} ms)`);
  } catch (error) {
    setRow("cad-engine", "ERROR", isEngineError(error) ? error.code : String(error));
    setLastAction(
      `Ping Engine failed: ${isEngineError(error) ? `${error.code}: ${error.message}` : String(error)}`,
    );
  }
}

async function handleRequestPreview(): Promise<void> {
  try {
    const { result: summary, ms } = await timed(requestPreviewSummary);
    setLastAction(
      `Request Preview Data: mesh received — schema=${summary.schema}, ` +
        `meshes=${summary.mesh_count}, vertices=${summary.total_vertices}, ` +
        `triangles=${summary.total_triangles}, lines=${summary.line_count} (${ms.toFixed(0)} ms). ` +
        `Not rendered by this button — use "Load / Refresh ZeroRod" for the 3D view.`,
    );
  } catch (error) {
    setLastAction(
      `Request Preview Data failed: ${isEngineError(error) ? `${error.code}: ${error.message}` : String(error)}`,
    );
  }
}

function handlePreviewStateChange(state: PreviewState, detail: string): void {
  setRow("3d-preview", previewStateToStatusValue(state));
  setLastAction(`Load / Refresh ZeroRod: ${detail}`);
}

const preview = createPreviewController(viewportEl, handlePreviewStateChange);
// Build 023 M4: the panel's live-preview scheduler and its Apply fallback
// both drive the same fetch/commit pair the "Load / Refresh ZeroRod"
// button's preview.load() is itself built from — one pipeline, per the M4
// mandate — but they need the fetch and commit steps separately so a
// stale (superseded) result can be discarded before it ever reaches the
// scene (see live_preview.ts and parameter_panel.ts's module doc comments).
const parameterPanel = createParameterPanelController(parameterPanelEl, {
  fetchPreview: preview.fetchPreview,
  commitPreview: preview.commitPreview,
});

document.querySelector<HTMLButtonElement>("#start-check-engine")!.addEventListener("click", () => {
  void handleStartCheckEngine();
});
document.querySelector<HTMLButtonElement>("#ping-engine")!.addEventListener("click", () => {
  void handlePingEngine();
});
document.querySelector<HTMLButtonElement>("#request-preview")!.addEventListener("click", () => {
  void handleRequestPreview();
});
document.querySelector<HTMLButtonElement>("#load-zerorod")!.addEventListener("click", () => {
  void preview.load();
});

window.addEventListener("beforeunload", () => {
  preview.dispose();
  parameterPanel.dispose();
});

async function init(): Promise<void> {
  renderStatusPanel();

  try {
    const info = await fetchAppInfo();
    setRow("rust-bridge", "READY", `${info.name} ${info.version} (${info.milestone})`);
  } catch (error) {
    setRow("rust-bridge", "ERROR", String(error));
  }

  try {
    const status = await fetchEngineStatus();
    setRow("python-sidecar", lifecycleToStatusValue(status.state));
  } catch (error) {
    setRow("python-sidecar", "ERROR", String(error));
  }

  // Loads canonical defaults through the real parameters_defaults →
  // engine_parameters_defaults path (§40/§41 of the M2 mandate) — the
  // panel's own loading/error states cover failure, nothing further to
  // surface on the shared status panel.
  void parameterPanel.load();
}

init();
