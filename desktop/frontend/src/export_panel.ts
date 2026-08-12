// Build 024 M2 — the export UI. Owns the actual "Export Model…" trigger,
// the native directory dialog invocation, the overwrite-conflict preflight,
// the in-panel overwrite confirmation, the export request itself, and
// success/error presentation. Deliberately isolated from parameter state,
// the renderer, and the live-preview scheduler (§36 of the M2 mandate) —
// this module only talks to the rest of the app through the small
// `ExportPanelIO` interface (mirroring how `PreviewIO` connects
// parameter_panel.ts to preview.ts without either importing the other's
// internals), and to the sidecar/Rust boundary through export.ts's already
// M1-proven, tested wrappers.
//
// Export always sources `io.getAcceptedRequest()` — the same "last
// successfully represented/accepted model state" parameter_panel.ts already
// exposes — never a draft (§11 of the mandate: a hard invariant, not a
// preference). The trigger is additionally disabled while live preview is
// pending or in flight (§30: "Strong preference: disable export until
// live-preview settles"), even though export sourcing `accepted` alone
// already prevents exporting an invisible draft — this is purely about
// "Export" always meaning "the model I am currently looking at" from the
// user's perspective, not a correctness requirement.

import { isEngineError } from "./engine";
import {
  requestExport,
  requestExportPreflight,
  selectExportDirectory,
  type ExportPreflightFile,
  type ExportResult,
} from "./export";
import type { ParametersRequest } from "./parameters";
import type { LivePreviewStatus } from "./parameter_panel";

/** How long an export must still be running before "Exporting…" actually
 * becomes visible — same reasoning and delay as parameter_panel.ts's
 * `UPDATING_DISPLAY_DELAY_MS` (§16 of the mandate: export is normally
 * ~0.13 s warm, so most exports should never show this at all). */
const EXPORTING_DISPLAY_DELAY_MS = 150;

export interface ExportPanelIO {
  /** The last successfully accepted (previewed or metadata-only-accepted)
   * parameter state, wrapped as a zerorod-parameters/v1 request — null
   * until defaults have loaded. Never the draft (§11/§30 of the mandate). */
  getAcceptedRequest: () => ParametersRequest | null;
  /** Current live-preview state-machine position — used to disable the
   * export trigger while a preview request is pending/updating (§12/§30). */
  getLivePreviewStatus: () => LivePreviewStatus;
}

export interface ExportPanelController {
  /** Re-evaluates the trigger's enabled/disabled state and re-renders if it
   * changed — call whenever `io`'s underlying state might have changed
   * (parameter_panel.ts's `onChange` hook wires this). */
  refreshEnablement: () => void;
  /** Releases any pending "Exporting…" display timer. Call once when the
   * panel is being torn down (e.g. page/app unload). */
  dispose: () => void;
}

type ExportPanelState =
  | { kind: "idle"; note?: string }
  | { kind: "selecting_destination" }
  | { kind: "checking_destination" }
  | { kind: "confirm_overwrite"; outputDirectory: string; conflicts: ExportPreflightFile[] }
  | { kind: "exporting"; showText: boolean }
  | { kind: "success"; result: ExportResult }
  | { kind: "error"; message: string };

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Maps a thrown `EngineError` (or anything else) to a concise, user-facing
 * message — never a raw code, never a raw traceback (§20 of the mandate).
 * `export_incomplete` gets its own message surfacing which output(s) are
 * missing (§21 — a partial write must never read as success). */
function formatExportError(error: unknown): string {
  if (!isEngineError(error)) return String(error);

  switch (error.code) {
    case "invalid_destination":
    case "export_invalid_destination":
      return "The selected destination is not valid. Choose a different folder.";
    case "export_permission_denied":
      return "Permission denied writing to the selected destination.";
    case "export_write_failed":
      return "The selected destination could not be written to.";
    case "export_incomplete": {
      const missing = (error.details as { missing?: unknown } | undefined)?.missing;
      const missingText = Array.isArray(missing) && missing.length > 0 ? missing.join(", ") : "one or more files";
      return `Export did not complete — missing: ${missingText}. Nothing was fully exported; try again.`;
    }
    case "invalid_parameters_domain":
    case "invalid_parameter_type":
    case "invalid_parameters":
    case "invalid_parameters_schema":
      return "The current model parameters are invalid; fix them before exporting.";
    case "invalid_export_result":
      // Build 024 M3 (§10/§23/§34 of the mandate): the sidecar's response
      // failed Rust-side structural validation (commands.rs's
      // validate_export_result/validate_export_preflight_result) — treated
      // as a hard failure, never partial success, exactly like
      // export_incomplete above.
      return "Export failed: the engine returned an unexpected result. Try again.";
    default:
      return `Export failed: ${error.message}`;
  }
}

export function createExportPanelController(
  container: HTMLElement,
  io: ExportPanelIO,
): ExportPanelController {
  let state: ExportPanelState = { kind: "idle" };
  let exportingDisplayTimer: ReturnType<typeof setTimeout> | null = null;

  function clearExportingTimer(): void {
    if (exportingDisplayTimer !== null) {
      clearTimeout(exportingDisplayTimer);
      exportingDisplayTimer = null;
    }
  }

  function isTriggerEnabled(): boolean {
    if (state.kind !== "idle" && state.kind !== "success" && state.kind !== "error") return false;
    if (!io.getAcceptedRequest()) return false;
    const status = io.getLivePreviewStatus();
    return status === "up-to-date" || status === "error";
  }

  function render(): void {
    const enabled = isTriggerEnabled();
    const triggerHtml = `<button type="button" class="export-trigger" data-action="export" ${enabled ? "" : "disabled"}>Export Model…</button>`;

    let bodyHtml = "";
    if (state.kind === "idle" && state.note) {
      bodyHtml = `<p class="export-note">${escapeHtml(state.note)}</p>`;
    } else if (state.kind === "exporting" && state.showText) {
      bodyHtml = `<p class="export-status">Exporting…</p>`;
    } else if (state.kind === "confirm_overwrite") {
      const items = state.conflicts.map((f) => `<li>${escapeHtml(f.filename)}</li>`).join("");
      bodyHtml = `
        <div class="export-confirm" role="alertdialog">
          <p>${state.conflicts.length} existing file(s) in this folder will be replaced:</p>
          <ul>${items}</ul>
          <div class="export-confirm-actions">
            <button type="button" data-action="cancel-overwrite">Cancel</button>
            <button type="button" data-action="confirm-overwrite">Replace</button>
          </div>
        </div>
      `;
    } else if (state.kind === "success") {
      const items = state.result.files
        .map((f) => `<li>${escapeHtml(f.filename)}</li>`)
        .join("");
      bodyHtml = `
        <div class="export-success" data-state="success">
          <p>Export completed to ${escapeHtml(state.result.output_directory)}</p>
          <ul>${items}</ul>
        </div>
      `;
    } else if (state.kind === "error") {
      bodyHtml = `<p class="export-error" role="alert">${escapeHtml(state.message)}</p>`;
    }

    container.innerHTML = `
      <div class="export-panel" data-state="${state.kind}">
        ${triggerHtml}
        ${bodyHtml}
      </div>
    `;

    container.querySelector('[data-action="export"]')?.addEventListener("click", () => {
      void handleExportClick();
    });
    container.querySelector('[data-action="cancel-overwrite"]')?.addEventListener("click", () => {
      handleCancelOverwrite();
    });
    container.querySelector('[data-action="confirm-overwrite"]')?.addEventListener("click", () => {
      void handleConfirmOverwrite();
    });
  }

  function setState(next: ExportPanelState): void {
    clearExportingTimer();
    state = next;
    render();
  }

  async function handleExportClick(): Promise<void> {
    if (!isTriggerEnabled()) return;
    const accepted = io.getAcceptedRequest();
    if (!accepted) return;

    setState({ kind: "selecting_destination" });
    let directory: string | null;
    try {
      directory = await selectExportDirectory();
    } catch (error) {
      setState({ kind: "error", message: formatExportError(error) });
      return;
    }

    // Cancellation is normal, never an error (§14 of the mandate) — no
    // export request is ever dispatched, the app stays unchanged.
    if (directory === null) {
      setState({ kind: "idle", note: "Export cancelled" });
      return;
    }

    await runPreflightThenExport(accepted, directory);
  }

  async function runPreflightThenExport(accepted: ParametersRequest, directory: string): Promise<void> {
    setState({ kind: "checking_destination" });
    let preflight;
    try {
      preflight = await requestExportPreflight(accepted.values, directory);
    } catch (error) {
      setState({ kind: "error", message: formatExportError(error) });
      return;
    }

    if (preflight.has_conflicts) {
      setState({ kind: "confirm_overwrite", outputDirectory: directory, conflicts: preflight.conflicts });
      return;
    }

    await runExport(accepted, directory);
  }

  function handleCancelOverwrite(): void {
    // No export request, no files changed, back to idle (§27 of the mandate).
    setState({ kind: "idle" });
  }

  async function handleConfirmOverwrite(): Promise<void> {
    if (state.kind !== "confirm_overwrite") return;
    const accepted = io.getAcceptedRequest();
    if (!accepted) {
      setState({ kind: "error", message: "No model state is currently available to export." });
      return;
    }
    await runExport(accepted, state.outputDirectory);
  }

  async function runExport(accepted: ParametersRequest, directory: string): Promise<void> {
    setState({ kind: "exporting", showText: false });
    exportingDisplayTimer = setTimeout(() => {
      exportingDisplayTimer = null;
      if (state.kind === "exporting") {
        state = { kind: "exporting", showText: true };
        render();
      }
    }, EXPORTING_DISPLAY_DELAY_MS);

    try {
      const result = await requestExport(accepted.values, directory);
      setState({ kind: "success", result });
    } catch (error) {
      setState({ kind: "error", message: formatExportError(error) });
    }
  }

  function refreshEnablement(): void {
    // Only the idle/success/error states have a live trigger whose
    // enablement can change out from under them (mid-flow states are always
    // disabled regardless) — re-render unconditionally is cheap (this panel
    // holds no focused text input, unlike parameter_panel.ts) and keeps this
    // function trivially correct.
    render();
  }

  function dispose(): void {
    clearExportingTimer();
  }

  render();

  return { refreshEnablement, dispose };
}
