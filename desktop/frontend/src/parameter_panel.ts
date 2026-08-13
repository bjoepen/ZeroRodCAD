// Build 023 M2 — the parameter panel DOM component. Owns rendering the
// grouped controls, wiring input events to the local draft
// (parameter_state.ts), and surfacing loading/error/status/validation
// feedback. The DOM tree is built once per successful load and mutated
// surgically afterward (only the changed field's error text / the live
// status line / the apply button are touched per keystroke) so typing
// never loses focus or cursor position.
//
// Build 023 M3 connected Apply to the real engine via an injected
// `applyParameters` callback.
//
// Build 023 M4 replaces that with automatic, debounced live preview
// (live_preview.ts's `createLivePreviewController`) — editing a
// geometry-affecting field now schedules a preview request on its own;
// Apply becomes an explicit "do it now" / retry action sharing the exact
// same scheduler, request, and stale-response protection (§2/§16/§22 of
// the M4 mandate: one pipeline, not two). `previewIO` (main.ts wires in
// `preview.fetchPreview`/`preview.commitPreview`) replaces the old
// `applyParameters` callback — the fetch/commit split lets this module gate
// scene mutation on the live-preview controller's generation check.
//
// State semantics chosen for M4 (§17/§18 of the mandate — documented, not
// left implicit): `accepted` now means "the parameter values currently
// represented in the preview, or the last state a completed engine round
// trip (live or Apply-triggered) confirmed" — M3's separate "accepted"
// concept and a hypothetical new "previewed" concept are deliberately
// merged into this one, since M4 makes every successful engine round trip
// go through the same commit path regardless of trigger. Dirty
// (`isDraftDirty(draft, accepted)`) stays meaningful: it now means "the
// draft hasn't been reflected in the preview yet" (still debouncing,
// invalid, or the last attempt errored) rather than "you must remember to
// click a button."

import { isEngineError } from "./engine";
import { createLivePreviewController, type LivePreviewController } from "./live_preview";
import {
  groupedParameterFields,
  PARAMETER_FIELDS_BY_KEY,
  type ParameterFieldMeta,
} from "./parameter_metadata";
import {
  buildParametersRequest,
  fetchDefaultParameters,
  type ParametersRequest,
  type ZeroRodParametersValues,
} from "./parameters";
import type { FetchPreviewResult, ParsedPreviewData, PreviewLoadResult } from "./preview";
import {
  addGauge,
  cloneValues,
  draftFromValues,
  hasDraftErrors,
  isDraftDirty,
  isGeometryUnchanged,
  removeGauge,
  resetDraft,
  serializeDraft,
  SCALAR_FIELDS,
  updateGauge,
  updateScalarField,
  valuesEqual,
  type ParameterDraftState,
  type ScalarFieldKey,
} from "./parameter_state";

/** The debounce delay for live preview (§10 of the M4 mandate). Chosen from
 * the measured warm engine round trip (~0.12–0.125 s, unchanged since M1)
 * plus normal desktop numeric-entry typing cadence: long enough that a
 * continuous edit ("38" → "4" → "45" → "6" → "60") collapses into one
 * request instead of five, short enough that the total stable-edit →
 * preview latency (debounce + engine round trip ≈ 300 ms + 125 ms ≈
 * 425 ms) still reads as "the model follows me," not "the app is slow." */
export const LIVE_PREVIEW_DEBOUNCE_MS = 300;

/** How long a request must still be running before "Updating preview…"
 * actually becomes visible (§28 of the mandate) — shorter than this and the
 * status text simply never changes from "Editing…", avoiding a flash for
 * the common ~125 ms case. */
const UPDATING_DISPLAY_DELAY_MS = 150;

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderFieldHtml(meta: ParameterFieldMeta, draft: ParameterDraftState): string {
  const inputId = `param-${meta.field}`;
  const errorId = `${inputId}-error`;
  const unitHtml = meta.unit ? `<span class="parameter-unit">${escapeHtml(meta.unit)}</span>` : "";
  const descriptionHtml = meta.description
    ? `<p class="parameter-description">${escapeHtml(meta.description)}</p>`
    : "";

  if (meta.kind === "gauge-array") {
    return `
      <div class="parameter-field parameter-field--gauges" data-field="${meta.field}">
        <span class="parameter-field-label">${escapeHtml(meta.label)}</span>
        <div class="gauge-list"></div>
        <button type="button" class="gauge-add" data-action="add-gauge">Add gauge</button>
        ${descriptionHtml}
      </div>
    `;
  }

  const rawValue = draft.raw[meta.field as ScalarFieldKey];
  const inputMode = meta.kind === "number" ? ' inputmode="decimal"' : "";
  const metadataBadge = meta.isMetadata ? '<span class="parameter-metadata-badge">metadata</span>' : "";

  return `
    <div class="parameter-field" data-field="${meta.field}">
      <label for="${inputId}">${escapeHtml(meta.label)}${metadataBadge}</label>
      <div class="parameter-field-control">
        <input id="${inputId}" type="text"${inputMode} autocomplete="off"
          value="${escapeHtml(rawValue)}" aria-describedby="${errorId}" aria-invalid="false" />
        ${unitHtml}
      </div>
      <p id="${errorId}" class="parameter-error" role="alert"></p>
      ${descriptionHtml}
    </div>
  `;
}

/** Build 023 M4 — the two engine-facing primitives the panel needs, wired
 * by main.ts from a single shared `preview.ts` `PreviewController`
 * instance. The panel never imports Three.js or calls `invoke()` itself. */
export interface PreviewIO {
  fetchPreview: (values: Partial<ZeroRodParametersValues>) => Promise<FetchPreviewResult>;
  commitPreview: (data: ParsedPreviewData) => void;
}

export type LivePreviewStatus = "up-to-date" | "pending" | "updating" | "error";

/** Build 025 M2 — distinguishes which startup step failed, without this
 * module needing to know anything about how a caller presents that (the
 * startup coordinator's job — see startup.ts). `defaults` means the
 * `parameters_defaults` round trip itself failed (before any form existed);
 * `preview` means defaults loaded fine but the automatic initial-preview
 * fetch for those same (always domain-valid) canonical values failed —
 * structurally an engine/sidecar-level failure (crash/timeout between the
 * two round trips), not a domain-validation error, so it is reported
 * distinctly from an ordinary live-preview failure even though it reuses
 * the exact same fetch/commit pipeline. */
export type ParameterPanelLoadResult =
  | { ok: true }
  | { ok: false; stage: "defaults" | "preview"; error: unknown };

export interface ParameterPanelController {
  /** Fetches canonical defaults through the real engine path
   * (parameters_defaults → engine_parameters_defaults), renders the form,
   * and then — Build 025 M2 — performs one automatic initial preview
   * fetch+commit for those same defaults, through the identical
   * fetch/commit pipeline `loadProjectValues` and the live-preview
   * scheduler already use (§12 of the M2 mandate: no second preview
   * pipeline). Call once at startup; safe to call again as a Retry (it
   * re-attempts the whole sequence, including the sidecar lazy-spawn, from
   * scratch — §25 of the mandate). */
  load: () => Promise<ParameterPanelLoadResult>;
  /** The last successfully accepted (previewed or metadata-only-accepted)
   * parameter state, wrapped as a zerorod-parameters/v1 request — null
   * until defaults have loaded. */
  getAcceptedRequest: () => ParametersRequest | null;
  /** The last successfully accepted parameter values directly. */
  getAccepted: () => ZeroRodParametersValues | null;
  /** Current live-preview state-machine position — exposed for tests. */
  getLivePreviewStatus: () => LivePreviewStatus;
  /** Build 025 M1 (§22 of the mandate): true when the current draft differs
   * from `accepted` — including an invalid in-progress edit — i.e. there is
   * user input not yet reflected anywhere that would be saved. Deliberately
   * separate from project-dirty (project_state.ts's `isProjectDirty`), never
   * merged into it. */
  hasUncommittedDraft: () => boolean;
  /** Build 025 M1: rebuilds the form and draft/accepted state from an
   * explicit value set (New's canonical defaults, or an Open'd project's
   * parameters) — unlike `load`, this never touches the Reset-to-Defaults
   * target (still the canonical engine defaults, not `values`), and always
   * performs one real preview fetch+commit for `values` so the visible
   * model matches immediately (§10/§13 of the mandate). Requires `load` to
   * have already completed at least once (canonical defaults must be known
   * to serve as the Reset target). */
  loadProjectValues: (values: ZeroRodParametersValues) => Promise<PreviewLoadResult>;
  /** Releases the live-preview scheduler's timers. Call once when the panel
   * is being torn down (e.g. page/app unload). */
  dispose: () => void;
}

export function createParameterPanelController(
  container: HTMLElement,
  previewIO: PreviewIO,
  onChange?: () => void,
): ParameterPanelController {
  let draft: ParameterDraftState | null = null;
  let defaults: ZeroRodParametersValues | null = null;
  let accepted: ZeroRodParametersValues | null = null;
  let livePreview: LivePreviewController<ZeroRodParametersValues> | null = null;
  let livePreviewStatus: LivePreviewStatus = "up-to-date";
  let updatingDisplayTimer: ReturnType<typeof setTimeout> | null = null;

  const scalarInputs = new Map<ScalarFieldKey, HTMLInputElement>();
  const scalarErrorEls = new Map<ScalarFieldKey, HTMLElement>();
  let gaugeListEl: HTMLElement | null = null;
  let liveStatusEl: HTMLElement | null = null;
  let applyButtonEl: HTMLButtonElement | null = null;

  function renderLoading(): void {
    container.innerHTML = `<p class="parameter-panel-status" data-state="loading">Loading defaults…</p>`;
  }

  function renderLoadError(detail: string): void {
    container.innerHTML = `
      <div class="parameter-panel-status" data-state="error">
        <p>Could not load default parameters.</p>
        <p class="parameter-panel-error-detail">${escapeHtml(detail)}</p>
      </div>
    `;
  }

  /** Sets the live-preview status. `data-status` on the status element is
   * always updated synchronously (so tests and a11y tooling see the true
   * state immediately); the *text* for "updating" specifically is delayed
   * (§28 of the mandate) — see the module doc comment. */
  function setLiveStatus(status: LivePreviewStatus, errorMessage?: string): void {
    livePreviewStatus = status;
    if (liveStatusEl) liveStatusEl.dataset.status = status;
    // Build 024 M2: the export panel lives outside this module (§36 of the
    // M2 mandate — export UI logic stays isolated, not mixed into parameter
    // state) but its trigger's enablement depends on `accepted`/live-preview
    // status, both of which only ever change together with a call here
    // (including the synchronous onRequestStart -> "updating" transition, not
    // just onSettle) — so notifying from this single point, rather than from
    // updateStatusUI, is what actually keeps "disable export while preview is
    // in flight" true for an Apply-triggered request too, not just automatic
    // debounced edits.
    onChange?.();

    if (updatingDisplayTimer !== null) {
      clearTimeout(updatingDisplayTimer);
      updatingDisplayTimer = null;
    }

    if (status === "updating") {
      updatingDisplayTimer = setTimeout(() => {
        updatingDisplayTimer = null;
        if (livePreviewStatus === "updating" && liveStatusEl) {
          liveStatusEl.textContent = "Updating preview…";
        }
      }, UPDATING_DISPLAY_DELAY_MS);
      return;
    }

    if (liveStatusEl) {
      liveStatusEl.textContent =
        status === "up-to-date"
          ? "Up to date"
          : status === "pending"
            ? "Editing…"
            : `Could not update preview: ${errorMessage ?? "unknown error"}`;
    }
  }

  function updateApplyButton(): void {
    if (!draft || !accepted || !applyButtonEl) return;
    applyButtonEl.disabled = hasDraftErrors(draft) || !isDraftDirty(draft, accepted);
  }

  function updateStatusUI(): void {
    updateApplyButton();
  }

  /** The single post-edit hook every draft-mutating handler calls (§9/§11
   * of the mandate: validity + relevance gate scheduling, uniformly,
   * regardless of which field changed). Cancels a pending debounce when the
   * draft is currently invalid or doesn't differ from `accepted` in any
   * geometry-affecting way; otherwise (re)schedules with the freshest
   * snapshot, which naturally also handles "editing continued" (the
   * scheduler's own timer reset) and "edited back to the already-accepted
   * value before the debounce fired" (the scheduler's own dedup). */
  function reconcileLivePreview(): void {
    if (!draft || !accepted || !livePreview) {
      updateStatusUI();
      return;
    }
    if (hasDraftErrors(draft)) {
      livePreview.cancelPending();
      updateStatusUI();
      return;
    }
    if (isGeometryUnchanged(draft.values, accepted)) {
      livePreview.cancelPending();
      updateStatusUI();
      return;
    }
    setLiveStatus("pending");
    livePreview.schedule(cloneValues(draft.values));
    updateStatusUI();
  }

  function renderGaugeList(): void {
    if (!gaugeListEl || !draft) return;
    const currentDraft = draft;
    gaugeListEl.innerHTML = currentDraft.rawGauges
      .map((value, index) => {
        const error = currentDraft.gaugeErrors[index];
        return `
          <div class="gauge-item" data-gauge-index="${index}">
            <input type="text" inputmode="decimal" aria-label="String gauge ${index + 1}"
              aria-invalid="${error ? "true" : "false"}" value="${escapeHtml(value)}" />
            <span class="parameter-unit">in</span>
            <button type="button" class="gauge-remove" data-action="remove-gauge" data-index="${index}"
              ${currentDraft.rawGauges.length <= 1 ? "disabled" : ""}>Remove</button>
            <p class="parameter-error" role="alert">${error ? escapeHtml(error) : ""}</p>
          </div>
        `;
      })
      .join("");

    gaugeListEl.querySelectorAll<HTMLInputElement>("input").forEach((input, index) => {
      input.addEventListener("input", () => handleGaugeInput(index, input.value));
    });
    gaugeListEl.querySelectorAll<HTMLButtonElement>('[data-action="remove-gauge"]').forEach((button) => {
      const index = Number(button.dataset.index);
      button.addEventListener("click", () => handleRemoveGauge(index));
    });
  }

  function handleScalarInput(field: ScalarFieldKey, value: string): void {
    if (!draft) return;
    draft = updateScalarField(draft, field, value);
    const errorEl = scalarErrorEls.get(field);
    const errorText = draft.errors[field] ?? "";
    if (errorEl) errorEl.textContent = errorText;
    scalarInputs.get(field)?.setAttribute("aria-invalid", errorText ? "true" : "false");
    reconcileLivePreview();
  }

  function handleGaugeInput(index: number, value: string): void {
    if (!draft) return;
    draft = updateGauge(draft, index, value);
    const item = gaugeListEl?.querySelector(`[data-gauge-index="${index}"]`);
    const errorEl = item?.querySelector<HTMLElement>(".parameter-error");
    const errorText = draft.gaugeErrors[index] ?? "";
    if (errorEl) errorEl.textContent = errorText;
    item?.querySelector("input")?.setAttribute("aria-invalid", errorText ? "true" : "false");
    reconcileLivePreview();
  }

  function handleAddGauge(): void {
    if (!draft) return;
    draft = addGauge(draft);
    renderGaugeList();
    reconcileLivePreview();
  }

  function handleRemoveGauge(index: number): void {
    if (!draft) return;
    draft = removeGauge(draft, index);
    renderGaugeList();
    reconcileLivePreview();
  }

  /** Reset immediately restores the canonical defaults into the draft and
   * — a deliberate change from M3 — lets the normal live-preview
   * scheduling take over from there (§19 of the M4 mandate): it does not
   * itself dispatch anything, it just makes the draft valid-and-different
   * again, which `reconcileLivePreview` picks up exactly like any other
   * edit. If `accepted` already matches the defaults, the scheduler's own
   * dedup means nothing is dispatched at all. */
  function handleReset(): void {
    if (!defaults) return;
    draft = resetDraft(defaults);
    for (const field of SCALAR_FIELDS) {
      const input = scalarInputs.get(field);
      if (input) {
        input.value = draft.raw[field];
        input.setAttribute("aria-invalid", "false");
      }
      const errorEl = scalarErrorEls.get(field);
      if (errorEl) errorEl.textContent = "";
    }
    renderGaugeList();
    reconcileLivePreview();
  }

  function formatEngineError(error: unknown): {
    formMessage: string;
    fieldErrors: Partial<Record<ScalarFieldKey, string>>;
  } {
    if (isEngineError(error)) {
      const fieldErrors: Partial<Record<ScalarFieldKey, string>> = {};
      const details = error.details as { field?: unknown; errors?: unknown } | undefined;
      if (details && typeof details.field === "string" && details.field in PARAMETER_FIELDS_BY_KEY) {
        fieldErrors[details.field as ScalarFieldKey] = error.message;
      }
      if (Array.isArray(details?.errors) && details.errors.every((e) => typeof e === "string")) {
        return { formMessage: (details.errors as string[]).join(" "), fieldErrors };
      }
      return { formMessage: `${error.code}: ${error.message}`, fieldErrors };
    }
    return { formMessage: String(error), fieldErrors: {} };
  }

  function applyFieldErrors(fieldErrors: Partial<Record<ScalarFieldKey, string>>): void {
    for (const [field, message] of Object.entries(fieldErrors) as [ScalarFieldKey, string][]) {
      const errorEl = scalarErrorEls.get(field);
      if (errorEl) errorEl.textContent = message;
      scalarInputs.get(field)?.setAttribute("aria-invalid", "true");
    }
  }

  /** Explicit Apply: validates, then either accepts a metadata-only change
   * locally (§24/§35 — never touches the engine) or flushes the current
   * draft through the SAME live-preview controller `scheduleImmediate`
   * uses for everything else (§16/§22 of the M4 mandate — Apply shares the
   * pipeline and its stale-response protection, it just skips the debounce
   * wait). No local async/await needed here — `onSettle` (shared with the
   * automatic live-preview path) does all the resulting state updates. */
  function handleApply(): void {
    if (!draft || !accepted || !livePreview) return;
    if (hasDraftErrors(draft)) return;
    if (!isDraftDirty(draft, accepted)) return;
    if (!serializeDraft(draft).ok) return;

    const submittedValues = cloneValues(draft.values);
    if (isGeometryUnchanged(submittedValues, accepted)) {
      accepted = submittedValues;
      setLiveStatus("up-to-date");
      updateStatusUI();
      return;
    }
    livePreview.scheduleImmediate(submittedValues);
  }

  /** `resetTarget` is what "Reset to Defaults" restores — always the
   * canonical engine defaults. It equals `values` for the normal startup
   * `load()` path (defaults ARE the initial content), but Build 025 M1's
   * `loadProjectValues` passes the two separately: an opened project's
   * values populate the form/accepted state, while Reset must still target
   * the canonical defaults, never the just-opened project (§28 of the M1
   * mandate: Open must not redefine what "defaults" means). */
  function buildForm(values: ZeroRodParametersValues, resetTarget: ZeroRodParametersValues): void {
    draft = draftFromValues(values);
    defaults = resetTarget;
    accepted = cloneValues(values);
    scalarInputs.clear();
    scalarErrorEls.clear();

    livePreview?.dispose();
    livePreview = createLivePreviewController<ZeroRodParametersValues, ParsedPreviewData>({
      initialValue: cloneValues(values),
      debounceMs: LIVE_PREVIEW_DEBOUNCE_MS,
      isEqual: valuesEqual,
      request: (v) => previewIO.fetchPreview(v),
      onRequestStart: () => setLiveStatus("updating"),
      onSettle: (outcome) => {
        if (outcome.ok) {
          previewIO.commitPreview(outcome.data);
          accepted = outcome.value;
          setLiveStatus("up-to-date");
        } else {
          setLiveStatus("error", formatEngineError(outcome.error).formMessage);
          applyFieldErrors(formatEngineError(outcome.error).fieldErrors);
        }
        updateStatusUI();
      },
    });

    const groupsHtml = groupedParameterFields()
      .map(
        (entry) => `
          <fieldset class="parameter-group" data-group="${escapeHtml(entry.group)}">
            <legend>${escapeHtml(entry.group)}</legend>
            <div class="parameter-group-body">
              ${entry.fields.map((meta) => renderFieldHtml(meta, draft!)).join("")}
            </div>
          </fieldset>
        `,
      )
      .join("");

    container.innerHTML = `
      <div class="parameter-panel" data-state="ready">
        <div class="parameter-panel-header">
          <h2>Parameters</h2>
          <span class="parameter-live-status" data-status="up-to-date">Up to date</span>
        </div>
        <p class="parameter-panel-hint">
          Geometry changes preview automatically a moment after you stop editing. Apply updates
          immediately.
        </p>
        <form class="parameter-form" novalidate>
          ${groupsHtml}
        </form>
        <div class="parameter-panel-actions">
          <button type="button" data-action="reset">Reset to Defaults</button>
          <button type="button" data-action="apply">Apply</button>
        </div>
      </div>
    `;

    // No submit-type button exists, so pressing Enter in a text field has no
    // implicit-submission target per the HTML form-submission algorithm —
    // Enter deliberately does nothing here (§44 of the M4 mandate); this
    // listener is only a defensive backstop in case a future edit ever adds
    // one.
    container.querySelector("form")?.addEventListener("submit", (event) => event.preventDefault());

    liveStatusEl = container.querySelector<HTMLElement>(".parameter-live-status");
    applyButtonEl = container.querySelector<HTMLButtonElement>('[data-action="apply"]');

    gaugeListEl = container.querySelector<HTMLElement>(
      '[data-field="string_gauges_inch"] .gauge-list',
    );

    for (const field of SCALAR_FIELDS) {
      const meta = PARAMETER_FIELDS_BY_KEY[field];
      const input = container.querySelector<HTMLInputElement>(`[data-field="${meta.field}"] input`);
      const errorEl = container.querySelector<HTMLElement>(`[data-field="${meta.field}"] .parameter-error`);
      if (input) {
        scalarInputs.set(field, input);
        input.addEventListener("input", () => handleScalarInput(field, input.value));
      }
      if (errorEl) scalarErrorEls.set(field, errorEl);
    }

    container.querySelector('[data-action="add-gauge"]')?.addEventListener("click", handleAddGauge);
    container.querySelector('[data-action="reset"]')?.addEventListener("click", handleReset);
    container.querySelector('[data-action="apply"]')?.addEventListener("click", handleApply);

    renderGaugeList();
    setLiveStatus("up-to-date");
    updateStatusUI();
  }

  async function load(): Promise<ParameterPanelLoadResult> {
    renderLoading();
    let values: ZeroRodParametersValues;
    try {
      values = await fetchDefaultParameters();
    } catch (error) {
      renderLoadError(isEngineError(error) ? `${error.code}: ${error.message}` : String(error));
      return { ok: false, stage: "defaults", error };
    }
    buildForm(values, values);

    // Build 025 M2 (§10/§12 of the mandate): the automatic initial preview —
    // same fetch/commit pipeline as every other preview update, sourced from
    // the canonical defaults `buildForm` just accepted, so `accepted`/
    // `draft`/the rendered scene stay consistent with no new semantics.
    setLiveStatus("updating");
    const result = await previewIO.fetchPreview(values);
    if (result.ok) {
      previewIO.commitPreview(result.data);
      setLiveStatus("up-to-date");
      updateStatusUI();
      return { ok: true };
    }
    setLiveStatus("error", formatEngineError(result.error).formMessage);
    applyFieldErrors(formatEngineError(result.error).fieldErrors);
    updateStatusUI();
    return { ok: false, stage: "preview", error: result.error };
  }

  function hasUncommittedDraft(): boolean {
    if (!draft || !accepted) return false;
    return isDraftDirty(draft, accepted);
  }

  async function loadProjectValues(values: ZeroRodParametersValues): Promise<PreviewLoadResult> {
    // `defaults` should already be populated (main.ts's init() always calls
    // `load()` before any project action can be reached), but this stays
    // defensive rather than assuming a call-order invariant silently holds.
    const resetTarget = defaults ?? (await fetchDefaultParameters());
    buildForm(cloneValues(values), resetTarget);

    // §10/§13 of the M1 mandate: New/Open must drive the real preview
    // pipeline, not just populate form fields — the visible model must
    // match. Uses the same fetch/commit split live-preview already uses so
    // a slower-than-expected fetch here can't race a user edit that starts
    // immediately after (buildForm has already re-armed the live-preview
    // scheduler above, so any such edit schedules normally on top of this).
    const result = await previewIO.fetchPreview(values);
    if (result.ok) {
      previewIO.commitPreview(result.data);
      setLiveStatus("up-to-date");
      updateStatusUI();
      return { ok: true };
    }
    setLiveStatus("error", formatEngineError(result.error).formMessage);
    applyFieldErrors(formatEngineError(result.error).fieldErrors);
    updateStatusUI();
    return { ok: false, error: result.error };
  }

  function dispose(): void {
    livePreview?.dispose();
    if (updatingDisplayTimer !== null) {
      clearTimeout(updatingDisplayTimer);
      updatingDisplayTimer = null;
    }
  }

  return {
    load,
    getAcceptedRequest: () => (accepted ? buildParametersRequest(accepted) : null),
    getAccepted: () => accepted,
    getLivePreviewStatus: () => livePreviewStatus,
    hasUncommittedDraft,
    loadProjectValues,
    dispose,
  };
}
