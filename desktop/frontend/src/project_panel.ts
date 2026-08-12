// Build 025 M1 — the project persistence UI: New / Open… / Save / Save As…,
// the current-project/dirty indicator, and the unsaved-changes guard (Save /
// Discard / Cancel) for New, Open, and Quit. Mirrors export_panel.ts's
// isolation discipline (§36 of the Build 024 M2 mandate, still followed
// here): this module only talks to the rest of the app through the small
// `ProjectPanelIO` interface, and to the sidecar/Rust boundary through
// project.ts's already-proven invoke() wrappers.
//
// §35 of the M1 mandate: these are deliberately compact, temporary product
// controls — native macOS menus/shortcuts (File > New/Open/Save/Save As) are
// Build 025 M4's job. This panel is what those menu items will eventually
// dispatch into, not a permanent UI surface.
//
// Save always sources `io.getAccepted()` — never a draft — per §5/§6 of the
// mandate ("Save what is actually accepted by the model"), the direct
// analogue of Build 024's "Export what is actually visible" rule.

import { isEngineError } from "./engine";
import { fetchDefaultParameters, type ZeroRodParametersValues } from "./parameters";
import type { LivePreviewStatus } from "./parameter_panel";
import type { PreviewLoadResult } from "./preview";
import {
  requestProjectOpen,
  requestProjectSave,
  selectProjectOpenFile,
  selectProjectSaveFile,
} from "./project";
import {
  defaultSaveFileName,
  initialProjectSession,
  isProjectDirty,
  shouldGuardAgainstDataLoss,
  withNewProjectBaseline,
  withSavedBaseline,
  type ProjectSessionState,
} from "./project_state";

export interface ProjectPanelIO {
  /** The last successfully accepted parameter values — never the draft
   * (§5/§6 of the mandate). Null until the parameter panel has loaded. */
  getAccepted: () => ZeroRodParametersValues | null;
  /** §22 of the mandate — true when the current draft differs from
   * `accepted`, independent of `project_dirty`. */
  hasUncommittedDraft: () => boolean;
  /** Current live-preview state-machine position — gates Save/Save As the
   * same way Build 024's export trigger is gated (§23 of the mandate). */
  getLivePreviewStatus: () => LivePreviewStatus;
  /** Rebuilds the parameter panel's form/draft/accepted state from an
   * explicit value set and drives a real preview round trip for it
   * (parameter_panel.ts's `loadProjectValues`). */
  loadProjectValues: (values: ZeroRodParametersValues) => Promise<PreviewLoadResult>;
}

export interface ProjectPanelController {
  /** Re-evaluates trigger enablement and the dirty indicator, and re-renders
   * if anything changed — call whenever `io`'s underlying state might have
   * changed (main.ts wires this the same way it wires export_panel's). */
  refreshEnablement: () => void;
  /** Runs the unsaved-changes guard for a Quit/window-close request: if
   * nothing would be lost, resolves `true` immediately; otherwise shows the
   * Save/Discard/Cancel dialog and resolves once the user picks one (`true`
   * = proceed with closing, `false` = stay open). Never itself closes the
   * window — the caller (main.ts's `onCloseRequested` handler) decides what
   * to do with the result (§19/§20 of the mandate). */
  confirmQuit: () => Promise<boolean>;
  dispose: () => void;
}

type PendingAction = "new" | "open";

type ProjectPanelState =
  | { kind: "idle"; note?: string }
  | { kind: "busy"; label: string }
  | { kind: "confirm_unsaved"; forQuit: boolean; error?: string }
  | { kind: "error"; message: string };

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Maps a thrown `EngineError` (or anything else) to a concise, user-facing
 * message — never a raw code, never a raw traceback, mirroring
 * export_panel.ts's `formatExportError`. */
function formatProjectError(error: unknown): string {
  if (!isEngineError(error)) return String(error);

  switch (error.code) {
    case "project_not_found":
      return "That project file could not be found.";
    case "project_permission_denied":
      return "Permission denied accessing that project file.";
    case "project_read_failed":
      return "That project file could not be read.";
    case "project_write_failed":
      return "The project could not be saved to that location.";
    case "project_invalid":
      return "That file is not a valid ZeroRodCAD project.";
    case "project_version_unsupported":
      return "That project file was created by a newer, incompatible version of ZeroRodCAD.";
    case "invalid_parameters_domain":
    case "invalid_parameter_type":
    case "invalid_parameters":
    case "invalid_parameters_schema":
      return "The current model parameters are invalid; fix them before saving.";
    case "dialog_channel_closed":
      return "The native dialog closed unexpectedly. Try again.";
    default:
      return `Project operation failed: ${error.message}`;
  }
}

export function createProjectPanelController(
  container: HTMLElement,
  io: ProjectPanelIO,
): ProjectPanelController {
  let state: ProjectPanelState = { kind: "idle" };
  let session: ProjectSessionState = initialProjectSession();
  let pendingAction: PendingAction | null = null;
  let quitResolve: ((allow: boolean) => void) | null = null;

  function projectLabel(): string {
    if (session.currentPath === null) return "Untitled project";
    const parts = session.currentPath.split(/[/\\]/);
    return parts[parts.length - 1] || session.currentPath;
  }

  function isDirty(): boolean {
    return isProjectDirty(session, io.getAccepted());
  }

  function isSaveEnabled(): boolean {
    if (state.kind !== "idle" && state.kind !== "error") return false;
    if (!io.getAccepted()) return false;
    const status = io.getLivePreviewStatus();
    return status === "up-to-date" || status === "error";
  }

  function isNewOpenEnabled(): boolean {
    return state.kind === "idle" || state.kind === "error";
  }

  function render(): void {
    const newOpenEnabled = isNewOpenEnabled();
    const saveEnabled = isSaveEnabled();
    const dirty = isDirty();

    const headerHtml = `
      <div class="project-header">
        <span class="project-name">${escapeHtml(projectLabel())}</span>
        ${dirty ? '<span class="project-dirty-indicator" title="Unsaved changes">●&nbsp;unsaved changes</span>' : ""}
      </div>
    `;

    const buttonsHtml = `
      <div class="project-actions">
        <button type="button" data-action="new" ${newOpenEnabled ? "" : "disabled"}>New</button>
        <button type="button" data-action="open" ${newOpenEnabled ? "" : "disabled"}>Open…</button>
        <button type="button" data-action="save" ${saveEnabled ? "" : "disabled"}>Save</button>
        <button type="button" data-action="save-as" ${saveEnabled ? "" : "disabled"}>Save As…</button>
      </div>
    `;

    let bodyHtml = "";
    if (state.kind === "idle" && state.note) {
      bodyHtml = `<p class="project-note">${escapeHtml(state.note)}</p>`;
    } else if (state.kind === "busy") {
      bodyHtml = `<p class="project-status">${escapeHtml(state.label)}</p>`;
    } else if (state.kind === "error") {
      bodyHtml = `<p class="project-error" role="alert">${escapeHtml(state.message)}</p>`;
    } else if (state.kind === "confirm_unsaved") {
      const errorHtml = state.error
        ? `<p class="project-error" role="alert">${escapeHtml(state.error)}</p>`
        : "";
      bodyHtml = `
        <div class="project-confirm" role="alertdialog">
          <p>This project has unsaved changes. What would you like to do?</p>
          ${errorHtml}
          <div class="project-confirm-actions">
            <button type="button" data-action="guard-cancel">Cancel</button>
            <button type="button" data-action="guard-discard">Discard</button>
            <button type="button" data-action="guard-save">Save</button>
          </div>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="project-panel" data-state="${state.kind}">
        ${headerHtml}
        ${buttonsHtml}
        ${bodyHtml}
      </div>
    `;

    container.querySelector('[data-action="new"]')?.addEventListener("click", () => {
      guardThenRun("new");
    });
    container.querySelector('[data-action="open"]')?.addEventListener("click", () => {
      guardThenRun("open");
    });
    container.querySelector('[data-action="save"]')?.addEventListener("click", () => {
      void performSave();
    });
    container.querySelector('[data-action="save-as"]')?.addEventListener("click", () => {
      void performSaveAs();
    });
    container.querySelector('[data-action="guard-cancel"]')?.addEventListener("click", () => {
      handleGuardCancel();
    });
    container.querySelector('[data-action="guard-discard"]')?.addEventListener("click", () => {
      void handleGuardDiscard();
    });
    container.querySelector('[data-action="guard-save"]')?.addEventListener("click", () => {
      void handleGuardSave();
    });
  }

  function setState(next: ProjectPanelState): void {
    state = next;
    render();
  }

  async function saveTo(
    values: ZeroRodParametersValues,
    path: string,
  ): Promise<{ ok: true; path: string } | { ok: false; error: unknown }> {
    try {
      const result = await requestProjectSave(values, path);
      session = withSavedBaseline(result.path, values);
      return { ok: true, path: result.path };
    } catch (error) {
      return { ok: false, error };
    }
  }

  async function performSaveAs(): Promise<void> {
    const accepted = io.getAccepted();
    if (!accepted || !isSaveEnabled()) return;
    setState({ kind: "busy", label: "Choosing destination…" });
    let path: string | null;
    try {
      path = await selectProjectSaveFile(defaultSaveFileName(accepted.project_name));
    } catch (error) {
      setState({ kind: "error", message: formatProjectError(error) });
      return;
    }
    if (path === null) {
      setState({ kind: "idle" });
      return;
    }
    setState({ kind: "busy", label: "Saving…" });
    const outcome = await saveTo(accepted, path);
    if (outcome.ok) {
      setState({ kind: "idle", note: `Saved ${outcome.path}` });
    } else {
      setState({ kind: "error", message: formatProjectError(outcome.error) });
    }
  }

  async function performSave(): Promise<void> {
    const accepted = io.getAccepted();
    if (!accepted || !isSaveEnabled()) return;
    if (session.currentPath === null) {
      await performSaveAs();
      return;
    }
    setState({ kind: "busy", label: "Saving…" });
    const outcome = await saveTo(accepted, session.currentPath);
    if (outcome.ok) {
      setState({ kind: "idle", note: `Saved ${outcome.path}` });
    } else {
      setState({ kind: "error", message: formatProjectError(outcome.error) });
    }
  }

  async function performNew(): Promise<void> {
    setState({ kind: "busy", label: "Creating new project…" });
    let defaults: ZeroRodParametersValues;
    try {
      defaults = await fetchDefaultParameters();
    } catch (error) {
      setState({ kind: "error", message: formatProjectError(error) });
      return;
    }
    const result = await io.loadProjectValues(defaults);
    session = withNewProjectBaseline(defaults);
    setState(
      result.ok
        ? { kind: "idle" }
        : { kind: "idle", note: "New project created, but the preview could not be rendered." },
    );
  }

  async function performOpen(): Promise<void> {
    setState({ kind: "busy", label: "Opening…" });
    let path: string | null;
    try {
      path = await selectProjectOpenFile();
    } catch (error) {
      setState({ kind: "error", message: formatProjectError(error) });
      return;
    }
    if (path === null) {
      setState({ kind: "idle" });
      return;
    }

    let opened;
    try {
      opened = await requestProjectOpen(path);
    } catch (error) {
      // §12 of the mandate: Open must be atomic. Nothing has been touched
      // yet (loadProjectValues has not been called), so the current
      // project/draft/preview are exactly as they were before this click.
      setState({ kind: "error", message: formatProjectError(error) });
      return;
    }

    const result = await io.loadProjectValues(opened.values);
    session = withSavedBaseline(path, opened.values);
    setState(
      result.ok
        ? { kind: "idle" }
        : { kind: "idle", note: "Project opened, but the preview could not be rendered." },
    );
  }

  function guardThenRun(action: PendingAction): void {
    if (!isNewOpenEnabled()) return;
    const guardNeeded = shouldGuardAgainstDataLoss(session, io.getAccepted(), io.hasUncommittedDraft());
    if (!guardNeeded) {
      void (action === "new" ? performNew() : performOpen());
      return;
    }
    pendingAction = action;
    setState({ kind: "confirm_unsaved", forQuit: false });
  }

  function confirmQuit(): Promise<boolean> {
    const guardNeeded = shouldGuardAgainstDataLoss(session, io.getAccepted(), io.hasUncommittedDraft());
    if (!guardNeeded) return Promise.resolve(true);
    return new Promise<boolean>((resolve) => {
      quitResolve = resolve;
      pendingAction = null;
      setState({ kind: "confirm_unsaved", forQuit: true });
    });
  }

  function handleGuardCancel(): void {
    const wasQuit = state.kind === "confirm_unsaved" && state.forQuit;
    pendingAction = null;
    if (wasQuit) {
      quitResolve?.(false);
      quitResolve = null;
    }
    setState({ kind: "idle" });
  }

  async function handleGuardDiscard(): Promise<void> {
    if (state.kind !== "confirm_unsaved") return;
    await settleGuard(state.forQuit, true);
  }

  async function handleGuardSave(): Promise<void> {
    if (state.kind !== "confirm_unsaved") return;
    const forQuit = state.forQuit;
    const accepted = io.getAccepted();
    if (!accepted) {
      await settleGuard(forQuit, true);
      return;
    }

    let path = session.currentPath;
    if (path === null) {
      let chosen: string | null;
      try {
        chosen = await selectProjectSaveFile(defaultSaveFileName(accepted.project_name));
      } catch (error) {
        setState({ kind: "confirm_unsaved", forQuit, error: formatProjectError(error) });
        return;
      }
      if (chosen === null) {
        // §18 of the mandate: cancelling the Save-As sub-dialog cancels the
        // ORIGINAL New/Open/Quit action entirely — no data lost, nothing
        // proceeds.
        handleGuardCancel();
        return;
      }
      path = chosen;
    }

    const outcome = await saveTo(accepted, path);
    if (!outcome.ok) {
      setState({ kind: "confirm_unsaved", forQuit, error: formatProjectError(outcome.error) });
      return;
    }
    await settleGuard(forQuit, true);
  }

  /** Resolves the pending guard: for Quit, hands the result back to the
   * caller of `confirmQuit` without performing any action here (closing the
   * window is the caller's job). For New/Open, proceeds with the action
   * that was gated. */
  async function settleGuard(forQuit: boolean, proceed: boolean): Promise<void> {
    const action = pendingAction;
    pendingAction = null;
    if (forQuit) {
      quitResolve?.(proceed);
      quitResolve = null;
      setState({ kind: "idle" });
      return;
    }
    setState({ kind: "idle" });
    if (proceed && action === "new") await performNew();
    else if (proceed && action === "open") await performOpen();
  }

  function refreshEnablement(): void {
    render();
  }

  function dispose(): void {
    // No timers or subscriptions to release — kept for interface symmetry
    // with the other panel controllers (parameter/export/preview), all of
    // which are torn down uniformly from main.ts's beforeunload handler.
  }

  render();

  return { refreshEnablement, confirmQuit, dispose };
}
