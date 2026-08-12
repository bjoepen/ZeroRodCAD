/**
 * Renderer-independent status-panel model. Kept free of DOM/Tauri APIs so it
 * stays unit-testable without a WebView or a real Rust backend (Build 022
 * M1). M2 extends the row set (Python sidecar, CAD engine) and M3 adds the
 * 3D preview row — this module's shape does not need to change for either.
 */

export type StatusValue =
  | "READY"
  | "NOT_READY"
  | "STOPPED"
  | "RUNNING"
  | "CONNECTED"
  | "ERROR"
  | "NOT_IMPLEMENTED";

export interface StatusRow {
  id: string;
  label: string;
  value: StatusValue;
  detail?: string;
}

const STATUS_CSS_CLASS: Record<StatusValue, string> = {
  READY: "ok",
  RUNNING: "ok",
  CONNECTED: "ok",
  STOPPED: "neutral",
  NOT_READY: "neutral",
  NOT_IMPLEMENTED: "neutral",
  ERROR: "error",
};

export function statusCssClass(value: StatusValue): string {
  return STATUS_CSS_CLASS[value];
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function renderStatusRows(rows: StatusRow[]): string {
  return rows
    .map((row) => {
      const detail = row.detail
        ? `<span class="status-detail">${escapeHtml(row.detail)}</span>`
        : "";
      return `
        <div class="status-row" data-row-id="${escapeHtml(row.id)}">
          <span class="status-label">${escapeHtml(row.label)}</span>
          <span class="status-value status-value--${statusCssClass(row.value)}">${row.value}</span>
          ${detail}
        </div>
      `;
    })
    .join("");
}
