// Build 025 M2 — the Diagnostics view (§16/§17 of the mandate): relocates
// the technical information the old product-UI debug controls used to dump
// inline (the 5-row status panel, "Start/Check Engine", "Ping Engine", the
// raw "last action" log — see docs/migration/BUILD-025-LIFECYCLE-ANALYSIS.md
// §2/§3) into one place that is reachable but not part of the normal
// product flow (§15/§37 — no menu integration here, that is Build 025 M4's
// job once native menus exist). Read-only except one explicit "Refresh
// Status" action (§17 — legitimate; "Kill Sidecar"/"Start Python"/"Send Raw
// IPC" are not normal Diagnostics functions and are deliberately absent).
// Opening/closing/refreshing never touches preview, project, export, or
// dirty state (§38) — every call this module makes is one of the existing
// read-only status commands (`app_info`, `engine_status`,
// `engine_sidecar_status`), reused unmodified; nothing new was added to
// Rust or the sidecar for this (§52/§53).
//
// Mirrors project_panel.ts's isolation discipline: this module only talks
// to the rest of the app through the small `DiagnosticsIO` interface.

import type { AppInfo } from "./app_info";
import type { EngineStatusInfo, SidecarStatus } from "./engine";
import { isEngineError } from "./engine";
import { MESH_SCHEMA } from "./mesh";
import { PARAMETERS_SCHEMA } from "./parameters";
import { renderStatusRows, type StatusRow, type StatusValue } from "./status";

export interface DiagnosticsIO {
  fetchAppInfo: () => Promise<AppInfo>;
  fetchEngineStatus: () => Promise<EngineStatusInfo>;
  fetchSidecarStatus: () => Promise<SidecarStatus>;
}

export interface DiagnosticsPanelController {
  dispose: () => void;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatFetchError(error: unknown): string {
  return isEngineError(error) ? `${error.code}: ${error.message}` : String(error);
}

export function createDiagnosticsPanelController(
  container: HTMLElement,
  io: DiagnosticsIO,
): DiagnosticsPanelController {
  let open = false;
  let status: "idle" | "loading" | "loaded" | "error" = "idle";
  let rows: StatusRow[] = [];
  let errorDetail = "";

  function setRow(id: string, label: string, value: StatusValue, detail?: string): void {
    const index = rows.findIndex((row) => row.id === id);
    const row: StatusRow = { id, label, value, detail };
    if (index === -1) rows.push(row);
    else rows[index] = row;
  }

  async function refresh(): Promise<void> {
    status = "loading";
    render();

    try {
      const [appInfo, engineStatus, sidecarStatus] = await Promise.all([
        io.fetchAppInfo(),
        io.fetchEngineStatus(),
        io.fetchSidecarStatus().catch((error: unknown) => {
          // The sidecar may not have started yet (or may currently be
          // unreachable) without that being a Diagnostics-level failure —
          // engine_status's own state/last_error already covers that case;
          // this just leaves the sidecar-only rows blank instead of
          // aborting the whole refresh.
          return { error } as { error: unknown };
        }),
      ]);

      rows = [];
      setRow(
        "app",
        "Application build",
        "READY",
        `${appInfo.name} ${appInfo.version} — Build ${appInfo.build} ${appInfo.milestone}`,
      );
      setRow(
        "engine",
        "Engine status",
        engineStatus.state,
        engineStatus.pid !== null ? `pid ${engineStatus.pid}` : undefined,
      );
      if (engineStatus.last_error) {
        setRow(
          "last-error",
          "Last engine error",
          "ERROR",
          `${engineStatus.last_error.code}: ${engineStatus.last_error.message}`,
        );
      }
      if (!("error" in sidecarStatus)) {
        setRow("sidecar", "Sidecar status", "CONNECTED", `${sidecarStatus.status} · pid ${sidecarStatus.pid}`);
        setRow("python", "Python version", "READY", sidecarStatus.python_version);
        setRow(
          "cadquery",
          "CadQuery version",
          sidecarStatus.cadquery_version ? "READY" : "NOT_READY",
          sidecarStatus.cadquery_version ?? undefined,
        );
        setRow(
          "ocp",
          "OCP variant",
          sidecarStatus.ocp_variant ? "READY" : "NOT_READY",
          sidecarStatus.ocp_variant ?? undefined,
        );
      }
      setRow("parameters-protocol", "Parameters protocol", "READY", PARAMETERS_SCHEMA);
      setRow("mesh-protocol", "Mesh protocol", "READY", MESH_SCHEMA);

      status = "loaded";
    } catch (error) {
      status = "error";
      errorDetail = formatFetchError(error);
    }
    render();
  }

  function render(): void {
    const toggleLabel = open ? "Hide Diagnostics" : "Diagnostics";
    const toggleHtml = `<button type="button" class="diagnostics-toggle" data-action="diagnostics-toggle" aria-expanded="${open}">${toggleLabel}</button>`;

    if (!open) {
      container.innerHTML = toggleHtml;
      wireToggle();
      return;
    }

    let bodyHtml: string;
    if (status === "loading") {
      bodyHtml = `<p class="diagnostics-status">Loading…</p>`;
    } else if (status === "error") {
      bodyHtml = `
        <p class="diagnostics-status" role="alert">Could not load diagnostics.</p>
        <p class="diagnostics-error-detail">${escapeHtml(errorDetail)}</p>
      `;
    } else {
      bodyHtml = `<div class="status-panel">${renderStatusRows(rows)}</div>`;
    }

    container.innerHTML = `
      ${toggleHtml}
      <div class="diagnostics-panel" role="region" aria-label="Diagnostics">
        ${bodyHtml}
        <button type="button" class="diagnostics-refresh" data-action="diagnostics-refresh">Refresh Status</button>
      </div>
    `;
    wireToggle();
    container.querySelector('[data-action="diagnostics-refresh"]')?.addEventListener("click", () => {
      void refresh();
    });
  }

  function wireToggle(): void {
    container.querySelector('[data-action="diagnostics-toggle"]')?.addEventListener("click", () => {
      open = !open;
      if (open && status === "idle") {
        void refresh();
        return;
      }
      render();
    });
  }

  function dispose(): void {
    // No timers/subscriptions to release — kept for interface symmetry with
    // the other panel controllers.
  }

  render();

  return { dispose };
}
