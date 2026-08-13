// Build 025 M3 — the Instrument Report panel (§16-23 of the mandate).
// Mirrors project_panel.ts's/export_panel.ts's isolation discipline: talks
// to the rest of the app only through the small `ReportPanelIO` interface.
// Normal product functionality, not a Diagnostics concern (§26) — kept
// entirely separate from diagnostics_panel.ts.

import { isEngineError } from "./engine";
import { valuesEqual } from "./parameter_state";
import type { ZeroRodParametersValues } from "./parameters";
import { renderReportMarkdownToHtml, requestReport } from "./report";

export interface ReportPanelIO {
  /** The last successfully accepted parameter values — never a draft (§18
   * of the mandate: "what the user sees is what the report describes",
   * the same rule already established for export). Null until the
   * parameter panel has loaded. */
  getAccepted: () => ZeroRodParametersValues | null;
}

export interface ReportPanelController {
  /** Call whenever `accepted` might have changed (main.ts wires this into
   * the same onChange hook export_panel.ts/project_panel.ts already use).
   * A no-op unless the panel is currently open AND the accepted values
   * actually differ from what's currently shown (§21 — "follow
   * accepted-state transitions, not raw draft typing," and avoid firing a
   * request on every one of those transitions that isn't a real change). */
  refreshIfVisible: () => void;
  /** Build 025 M4 — the native View → Instrument Report menu entry point.
   * Opens the panel and fetches for the current accepted state, exactly
   * like clicking the visible toggle when closed — no second report
   * implementation/window (§18 of the mandate). Safe to call while already
   * open (just re-fetches, same as the visible toggle offers via Retry). */
  open: () => void;
  dispose: () => void;
}

type ReportPanelState =
  | { kind: "loading" }
  | { kind: "loaded"; html: string }
  | { kind: "error"; message: string };

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatReportError(error: unknown): string {
  return isEngineError(error) ? `${error.code}: ${error.message}` : String(error);
}

export function createReportPanelController(
  container: HTMLElement,
  io: ReportPanelIO,
): ReportPanelController {
  let open = false;
  let state: ReportPanelState | null = null;
  let lastFetchedFor: ZeroRodParametersValues | null = null;

  async function fetchReport(): Promise<void> {
    const accepted = io.getAccepted();
    if (!accepted) {
      state = { kind: "error", message: "No accepted model yet." };
      render();
      return;
    }
    state = { kind: "loading" };
    render();
    try {
      const result = await requestReport(accepted);
      lastFetchedFor = accepted;
      state = { kind: "loaded", html: renderReportMarkdownToHtml(result.markdown) };
    } catch (error) {
      // §22 of the mandate: a report failure must not touch preview,
      // accepted, or project state — nothing here does; it only sets this
      // panel's own local presentation state.
      state = { kind: "error", message: formatReportError(error) };
    }
    render();
  }

  function render(): void {
    const toggleLabel = open ? "Hide Instrument Report" : "Instrument Report";
    const toggleHtml = `<button type="button" class="report-toggle" data-action="report-toggle" aria-expanded="${open}">${toggleLabel}</button>`;

    if (!open || state === null) {
      container.innerHTML = toggleHtml;
      wireToggle();
      return;
    }

    let bodyHtml: string;
    if (state.kind === "loading") {
      bodyHtml = `<p class="report-status">Loading…</p>`;
    } else if (state.kind === "error") {
      bodyHtml = `
        <p class="report-status" role="alert">Could not load the Instrument Report.</p>
        <p class="report-error-detail">${escapeHtml(state.message)}</p>
        <button type="button" class="report-retry" data-action="report-retry">Retry</button>
      `;
    } else {
      bodyHtml = `<div class="report-content">${state.html}</div>`;
    }

    container.innerHTML = `
      ${toggleHtml}
      <div class="report-panel" role="region" aria-label="Instrument Report">
        ${bodyHtml}
      </div>
    `;
    wireToggle();
    container.querySelector('[data-action="report-retry"]')?.addEventListener("click", () => {
      void fetchReport();
    });
  }

  function openPanel(): void {
    open = true;
    void fetchReport();
  }

  function wireToggle(): void {
    container.querySelector('[data-action="report-toggle"]')?.addEventListener("click", () => {
      if (open) {
        open = false;
        render();
      } else {
        openPanel();
      }
    });
  }

  function refreshIfVisible(): void {
    if (!open) return;
    const accepted = io.getAccepted();
    if (!accepted) return;
    if (lastFetchedFor && valuesEqual(lastFetchedFor, accepted)) return;
    void fetchReport();
  }

  function dispose(): void {
    // No timers/subscriptions to release — kept for interface symmetry
    // with the other panel controllers.
  }

  render();

  return { refreshIfVisible, open: openPanel, dispose };
}
