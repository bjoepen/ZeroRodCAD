import "./style.css";
import { fetchAppInfo } from "./app_info";
import { renderStatusRows, type StatusRow } from "./status";

const appEl = document.querySelector<HTMLDivElement>("#app")!;

function render(rows: StatusRow[]): void {
  appEl.innerHTML = `
    <main class="foundation">
      <h1>ZeroRodCAD Desktop 2.0</h1>
      <p class="subtitle">Build 022 — Tauri Desktop Foundation</p>
      <section class="status-panel">${renderStatusRows(rows)}</section>
    </main>
  `;
}

async function init(): Promise<void> {
  const rows: StatusRow[] = [
    { id: "shell", label: "Desktop shell", value: "READY" },
    { id: "rust-bridge", label: "Rust bridge", value: "NOT_READY" },
    { id: "python-sidecar", label: "Python sidecar", value: "NOT_IMPLEMENTED", detail: "M2" },
    { id: "cad-engine", label: "CAD engine", value: "NOT_IMPLEMENTED", detail: "M2" },
    { id: "3d-preview", label: "3D preview", value: "NOT_IMPLEMENTED", detail: "M3" },
  ];
  render(rows);

  try {
    const info = await fetchAppInfo();
    rows[1] = {
      id: "rust-bridge",
      label: "Rust bridge",
      value: "READY",
      detail: `${info.name} ${info.version} (${info.milestone})`,
    };
  } catch (error) {
    rows[1] = {
      id: "rust-bridge",
      label: "Rust bridge",
      value: "ERROR",
      detail: String(error),
    };
  }
  render(rows);
}

init();
