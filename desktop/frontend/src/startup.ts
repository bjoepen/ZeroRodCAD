// Build 025 M2 — the startup presentation coordinator (§54 of the mandate:
// keep lifecycle/startup UX out of main.ts, in its own small module). Owns
// exactly one thing: showing the user a calm, non-blocking indication that
// ZeroRodCAD is preparing itself, and — only on genuine failure — a
// friendly retry surface. It knows nothing about Tauri, `invoke()`, or the
// parameter panel directly; `io.run()` is main.ts's one wiring point
// (`() => parameterPanel.load()`), which already performs the real
// defaults-load + automatic-initial-preview sequence (parameter_panel.ts).
//
// Anti-flicker (§20/§48 of the mandate): "Preparing ZeroRodCAD…" only
// appears if `run()` is still pending after PREPARING_DISPLAY_DELAY_MS —
// the same delayed-indicator idea parameter_panel.ts's own
// UPDATING_DISPLAY_DELAY_MS already established for live preview, reused
// here rather than invented a second time.
//
// No "ENGINE READY" banner (§21): on success this renders nothing at all —
// a normal product app signals ready by working, not by announcing it.

import type { ParameterPanelLoadResult } from "./parameter_panel";

const PREPARING_DISPLAY_DELAY_MS = 250;

type LoadFailure = Extract<ParameterPanelLoadResult, { ok: false }>;

export interface StartupIO {
  run: () => Promise<ParameterPanelLoadResult>;
}

export interface StartupController {
  /** Runs the startup sequence via `io.run()` and renders the outcome.
   * Call once at app init; Retry re-invokes this same function, so it
   * reuses the identical sequence (§25 of the mandate) rather than a
   * special-cased retry path. */
  start: () => Promise<void>;
  dispose: () => void;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Pure — the plain-language headline (§5 of the Lifecycle Analysis, §13 of
 * the M2 mandate): never a raw error code here — "Show Details" is the only
 * place that appears. */
export function friendlyStartupMessage(result: LoadFailure): string {
  return result.stage === "defaults"
    ? "ZeroRodCAD's engine could not start."
    : "ZeroRodCAD could not load the initial model.";
}

/** Pure — the sanitized technical detail "Show Details" reveals: a
 * structured EngineError's code/message, or a plain String() fallback.
 * Never a raw traceback, matching every other error surface in this app
 * (the sidecar boundary itself never emits one). */
export function startupErrorDetail(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error &&
    typeof (error as { code: unknown }).code === "string" &&
    typeof (error as { message: unknown }).message === "string"
  ) {
    return `${(error as { code: string }).code}: ${(error as { message: string }).message}`;
  }
  return String(error);
}

export function createStartupController(container: HTMLElement, io: StartupIO): StartupController {
  let preparingTimer: ReturnType<typeof setTimeout> | null = null;
  let detailsShown = false;

  function clearPreparingTimer(): void {
    if (preparingTimer !== null) {
      clearTimeout(preparingTimer);
      preparingTimer = null;
    }
  }

  function renderIdle(): void {
    container.innerHTML = "";
  }

  function renderPreparing(): void {
    container.innerHTML = `<p class="startup-status" role="status">Preparing ZeroRodCAD…</p>`;
  }

  function renderError(result: LoadFailure): void {
    detailsShown = false;
    const detail = startupErrorDetail(result.error);
    container.innerHTML = `
      <div class="startup-error" role="alert">
        <p>${escapeHtml(friendlyStartupMessage(result))}</p>
        <div class="startup-error-actions">
          <button type="button" data-action="startup-retry">Retry</button>
          <button type="button" data-action="startup-details" aria-expanded="false">Show Details</button>
        </div>
        <p class="startup-error-detail" hidden>${escapeHtml(detail)}</p>
      </div>
    `;
    container.querySelector('[data-action="startup-retry"]')?.addEventListener("click", () => {
      void start();
    });
    container.querySelector('[data-action="startup-details"]')?.addEventListener("click", (event) => {
      detailsShown = !detailsShown;
      const detailEl = container.querySelector<HTMLElement>(".startup-error-detail");
      if (detailEl) detailEl.hidden = !detailsShown;
      (event.currentTarget as HTMLButtonElement).setAttribute("aria-expanded", String(detailsShown));
    });
  }

  async function start(): Promise<void> {
    clearPreparingTimer();
    renderIdle();
    preparingTimer = setTimeout(() => {
      preparingTimer = null;
      renderPreparing();
    }, PREPARING_DISPLAY_DELAY_MS);

    const result = await io.run();

    clearPreparingTimer();
    if (result.ok) {
      renderIdle();
    } else {
      renderError(result);
    }
  }

  function dispose(): void {
    clearPreparingTimer();
  }

  return { start, dispose };
}
