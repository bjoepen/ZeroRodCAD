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
import { renderStatusRows, type StatusRow, type StatusValue } from "./status";

const appEl = document.querySelector<HTMLDivElement>("#app")!;

let lastAction = "";

function lifecycleToStatusValue(state: LifecycleState): StatusValue {
  return state; // StatusValue is a superset of LifecycleState
}

function render(rows: StatusRow[]): void {
  appEl.innerHTML = `
    <main class="foundation">
      <h1>ZeroRodCAD Desktop 2.0</h1>
      <p class="subtitle">Build 022 — Milestone 2: Productive Sidecar &amp; Rust Lifecycle</p>
      <section class="status-panel">${renderStatusRows(rows)}</section>
      <section class="actions">
        <button id="start-check-engine" type="button">Start / Check Engine</button>
        <button id="ping-engine" type="button">Ping Engine</button>
        <button id="request-preview" type="button">Request Preview Data</button>
      </section>
      <pre id="last-action" class="last-action">${lastAction}</pre>
    </main>
  `;

  document
    .querySelector<HTMLButtonElement>("#start-check-engine")!
    .addEventListener("click", () => void handleStartCheckEngine(rows));
  document
    .querySelector<HTMLButtonElement>("#ping-engine")!
    .addEventListener("click", () => void handlePingEngine(rows));
  document
    .querySelector<HTMLButtonElement>("#request-preview")!
    .addEventListener("click", () => void handleRequestPreview(rows));
}

function setRow(rows: StatusRow[], id: string, value: StatusValue, detail?: string): void {
  const index = rows.findIndex((row) => row.id === id);
  if (index !== -1) {
    rows[index] = { id, label: rows[index].label, value, detail };
  }
}

async function timed<T>(action: () => Promise<T>): Promise<{ result: T; ms: number }> {
  const started = performance.now();
  const result = await action();
  return { result, ms: performance.now() - started };
}

async function handleStartCheckEngine(rows: StatusRow[]): Promise<void> {
  try {
    const { result: ping, ms } = await timed(pingEngine);
    const status = await fetchEngineStatus();
    setRow(
      rows,
      "python-sidecar",
      lifecycleToStatusValue(status.state),
      `pid ${ping.pid} · ${ms.toFixed(0)} ms`,
    );
    lastAction = `Start / Check Engine: ok (pid ${ping.pid}, ${ms.toFixed(0)} ms)`;
  } catch (error) {
    setRow(rows, "python-sidecar", "ERROR", isEngineError(error) ? error.code : String(error));
    lastAction = `Start / Check Engine failed: ${isEngineError(error) ? `${error.code}: ${error.message}` : String(error)}`;
  }
  render(rows);
}

async function handlePingEngine(rows: StatusRow[]): Promise<void> {
  try {
    const { result: sidecarStatus, ms } = await timed(fetchSidecarStatus);
    setRow(
      rows,
      "cad-engine",
      "CONNECTED",
      `${sidecarStatus.cadquery_version ?? "?"} / ${sidecarStatus.ocp_variant ?? "?"} · vtk=${sidecarStatus.vtk_installed} · ${ms.toFixed(0)} ms`,
    );
    lastAction = `Ping Engine: ${JSON.stringify(sidecarStatus)} (${ms.toFixed(0)} ms)`;
  } catch (error) {
    setRow(rows, "cad-engine", "ERROR", isEngineError(error) ? error.code : String(error));
    lastAction = `Ping Engine failed: ${isEngineError(error) ? `${error.code}: ${error.message}` : String(error)}`;
  }
  render(rows);
}

async function handleRequestPreview(rows: StatusRow[]): Promise<void> {
  try {
    const { result: summary, ms } = await timed(requestPreviewSummary);
    lastAction =
      `Request Preview Data: mesh received — schema=${summary.schema}, ` +
      `meshes=${summary.mesh_count}, vertices=${summary.total_vertices}, ` +
      `triangles=${summary.total_triangles}, lines=${summary.line_count} (${ms.toFixed(0)} ms). ` +
      `Not rendered — 3D preview is M3.`;
  } catch (error) {
    lastAction = `Request Preview Data failed: ${isEngineError(error) ? `${error.code}: ${error.message}` : String(error)}`;
  }
  render(rows);
}

async function init(): Promise<void> {
  const rows: StatusRow[] = [
    { id: "shell", label: "Desktop shell", value: "READY" },
    { id: "rust-bridge", label: "Rust bridge", value: "NOT_READY" },
    { id: "python-sidecar", label: "Python sidecar", value: "STOPPED" },
    { id: "cad-engine", label: "CAD engine", value: "NOT_READY" },
    { id: "3d-preview", label: "3D preview", value: "NOT_IMPLEMENTED", detail: "M3" },
  ];
  render(rows);

  try {
    const info = await fetchAppInfo();
    setRow(rows, "rust-bridge", "READY", `${info.name} ${info.version} (${info.milestone})`);
  } catch (error) {
    setRow(rows, "rust-bridge", "ERROR", String(error));
  }

  try {
    const status = await fetchEngineStatus();
    setRow(rows, "python-sidecar", lifecycleToStatusValue(status.state));
  } catch (error) {
    setRow(rows, "python-sidecar", "ERROR", String(error));
  }

  render(rows);
}

init();
