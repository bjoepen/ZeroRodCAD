// Build 023 M2 — the parameter panel DOM component. Owns rendering the
// grouped controls, wiring input events to the local draft
// (parameter_state.ts), and surfacing loading/error/dirty/validation
// feedback. The DOM tree is built once per successful load and mutated
// surgically afterward (only the changed field's error text / the dirty
// badge / the apply button are touched per keystroke) so typing never loses
// focus or cursor position — a full innerHTML re-render per keystroke would
// break exactly the keyboard usability the mandate calls out.
//
// Build 023 M3 connects Apply to the real engine: `createParameterPanelController`
// now takes an `applyParameters` callback (main.ts wires it to
// `preview.load`, preview.ts's Three.js geometry-replacement path). Editing
// a field, adding/removing a gauge, or Reset still never call it — Apply is
// the *only* trigger (§9 of the M3 mandate). "Dirty" is redefined from "the
// draft differs from the loaded defaults" (M2) to "the draft differs from
// the last successfully accepted parameter state" (M3 §26) — `accepted`
// tracks that; `defaults` (the canonical default set) is kept separately,
// used only as Reset's target, per the M3 mandate's explicit split (§25).

import { isEngineError } from "./engine";
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
  type ParameterDraftState,
  type ScalarFieldKey,
} from "./parameter_state";

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

/** Build 023 M3 — the panel never calls the sidecar itself; it asks the
 * caller (main.ts, wiring in `preview.load`) to do it, and only reacts to
 * the outcome. This keeps the panel decoupled from Three.js/engine
 * internals, mirroring how `preview.ts` itself takes an `onStateChange`
 * callback instead of owning status-panel DOM. */
export type ApplyParametersFn = (
  values: ZeroRodParametersValues,
) => Promise<{ ok: boolean; error?: unknown }>;

export type ApplyStatus = "idle" | "applying" | "applied" | "error";

export interface ParameterPanelController {
  /** Fetches canonical defaults through the real engine path
   * (parameters_defaults → engine_parameters_defaults) and renders the
   * form. Call once at startup. */
  load: () => Promise<void>;
  /** The last successfully accepted parameter state, wrapped as a
   * zerorod-parameters/v1 request — null until the first successful Apply
   * (or before defaults have loaded at all). Derived from `accepted`, so it
   * always reflects the current session-accepted state (§27 of the M3
   * mandate: accepted is session state, not project persistence). */
  getAcceptedRequest: () => ParametersRequest | null;
  /** The last successfully accepted parameter values directly (no envelope
   * wrapper) — exposed for tests and future milestones. */
  getAccepted: () => ZeroRodParametersValues | null;
  /** Current Apply state machine position — exposed for tests. */
  getApplyStatus: () => ApplyStatus;
}

export function createParameterPanelController(
  container: HTMLElement,
  applyParameters: ApplyParametersFn,
): ParameterPanelController {
  let draft: ParameterDraftState | null = null;
  let defaults: ZeroRodParametersValues | null = null;
  let accepted: ZeroRodParametersValues | null = null;
  let applyStatus: ApplyStatus = "idle";

  const scalarInputs = new Map<ScalarFieldKey, HTMLInputElement>();
  const scalarErrorEls = new Map<ScalarFieldKey, HTMLElement>();
  let gaugeListEl: HTMLElement | null = null;
  let dirtyBadgeEl: HTMLElement | null = null;
  let applyButtonEl: HTMLButtonElement | null = null;
  let resetButtonEl: HTMLButtonElement | null = null;
  let applyMessageEl: HTMLElement | null = null;

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

  function updateDirtyBadge(): void {
    if (!draft || !accepted) return;
    dirtyBadgeEl?.classList.toggle("is-visible", isDraftDirty(draft, accepted));
  }

  /** Apply is blocked while invalid, while nothing differs from the last
   * accepted state (§36 of the M3 mandate — no unnecessary rebuild), and
   * while a request is already in flight (§15/§37 — no parallel requests).
   * Reset is only blocked while applying, so a stray click can't mutate the
   * draft out from under an in-flight request's already-captured snapshot. */
  function updateApplyButton(): void {
    if (!draft || !accepted) return;
    const applying = applyStatus === "applying";
    if (applyButtonEl) {
      applyButtonEl.disabled = applying || hasDraftErrors(draft) || !isDraftDirty(draft, accepted);
      applyButtonEl.textContent = applying ? "Applying…" : "Apply";
    }
    if (resetButtonEl) {
      resetButtonEl.disabled = applying;
    }
  }

  function updateStatusUI(): void {
    updateDirtyBadge();
    updateApplyButton();
  }

  function showApplyMessage(state: "ok" | "error" | "applying", text: string): void {
    if (!applyMessageEl) return;
    applyMessageEl.classList.add("is-visible");
    applyMessageEl.dataset.state = state;
    applyMessageEl.textContent = text;
  }

  function clearApplyMessage(): void {
    if (!applyMessageEl) return;
    applyMessageEl.classList.remove("is-visible");
    applyMessageEl.textContent = "";
    delete applyMessageEl.dataset.state;
  }

  /** A fresh edit after a settled Apply (applied or error) makes that
   * outcome message stale — clear it rather than leave a misleading
   * "Applied"/error message next to a draft that has since changed again. */
  function clearStaleApplyOutcome(): void {
    if (applyStatus === "applied" || applyStatus === "error") {
      applyStatus = "idle";
      clearApplyMessage();
    }
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
    clearStaleApplyOutcome();
    draft = updateScalarField(draft, field, value);
    const errorEl = scalarErrorEls.get(field);
    const errorText = draft.errors[field] ?? "";
    if (errorEl) errorEl.textContent = errorText;
    scalarInputs.get(field)?.setAttribute("aria-invalid", errorText ? "true" : "false");
    updateStatusUI();
  }

  function handleGaugeInput(index: number, value: string): void {
    if (!draft) return;
    clearStaleApplyOutcome();
    draft = updateGauge(draft, index, value);
    const item = gaugeListEl?.querySelector(`[data-gauge-index="${index}"]`);
    const errorEl = item?.querySelector<HTMLElement>(".parameter-error");
    const errorText = draft.gaugeErrors[index] ?? "";
    if (errorEl) errorEl.textContent = errorText;
    item?.querySelector("input")?.setAttribute("aria-invalid", errorText ? "true" : "false");
    updateStatusUI();
  }

  function handleAddGauge(): void {
    if (!draft) return;
    clearStaleApplyOutcome();
    draft = addGauge(draft);
    renderGaugeList();
    updateStatusUI();
  }

  function handleRemoveGauge(index: number): void {
    if (!draft) return;
    clearStaleApplyOutcome();
    draft = removeGauge(draft, index);
    renderGaugeList();
    updateStatusUI();
  }

  /** Reset only ever touches the local draft — never calls applyParameters
   * (§25 of the M3 mandate: reset does not regenerate). It restores the
   * canonical defaults into the draft, not into `accepted` — if `accepted`
   * currently differs from `defaults` (some other state was already
   * Applied), the draft becomes dirty again and Apply is required to
   * actually restore the default geometry, exactly as the mandate
   * specifies. */
  function handleReset(): void {
    if (!defaults || applyStatus === "applying") return;
    draft = resetDraft(defaults);
    applyStatus = "idle";
    clearApplyMessage();
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
    updateStatusUI();
  }

  function formatApplyError(error: unknown): {
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

  /** The sole geometry-regeneration trigger in M3 (§9 of the mandate).
   * `applyStatus` is set to "applying" synchronously, before any `await` —
   * since JS runs that prefix to completion before yielding, no second
   * invocation (double click, Enter-triggered re-entry, etc.) can slip in
   * between the guard check and the flag being set (§15/§37). A snapshot of
   * the values actually being submitted is captured up front, so a
   * concurrent edit to `draft` while the request is in flight cannot alter
   * what gets recorded as accepted on success (§17/§21 of the mandate —
   * atomic w.r.t. the in-flight request). */
  async function handleApply(): Promise<void> {
    if (!draft || !accepted) return;
    if (applyStatus === "applying") return;
    if (hasDraftErrors(draft)) return;
    if (!isDraftDirty(draft, accepted)) return;
    if (!serializeDraft(draft).ok) return;

    const submittedValues = cloneValues(draft.values);
    applyStatus = "applying";
    updateStatusUI();

    // project_name-only changes never affect the generated geometry (§24 of
    // the mandate) — accept locally without a wasted engine round trip.
    if (isGeometryUnchanged(submittedValues, accepted)) {
      accepted = submittedValues;
      applyStatus = "applied";
      showApplyMessage("ok", "Applied locally — metadata only, no geometry regeneration needed.");
      updateStatusUI();
      return;
    }

    showApplyMessage("applying", "Requesting updated geometry…");
    const result = await applyParameters(submittedValues);

    if (result.ok) {
      accepted = submittedValues;
      applyStatus = "applied";
      showApplyMessage("ok", "Applied — preview updated.");
    } else {
      applyStatus = "error";
      const { formMessage, fieldErrors } = formatApplyError(result.error);
      showApplyMessage("error", formMessage);
      applyFieldErrors(fieldErrors);
    }
    updateStatusUI();
  }

  function buildForm(values: ZeroRodParametersValues): void {
    draft = draftFromValues(values);
    defaults = values;
    accepted = cloneValues(values);
    applyStatus = "idle";
    scalarInputs.clear();
    scalarErrorEls.clear();

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
          <span class="parameter-dirty-badge">Unsaved parameter changes</span>
        </div>
        <p class="parameter-panel-hint">
          Press Apply to send your changes to the engine and update the 3D preview.
        </p>
        <form class="parameter-form" novalidate>
          ${groupsHtml}
        </form>
        <div class="parameter-panel-actions">
          <button type="button" data-action="reset">Reset to Defaults</button>
          <button type="button" data-action="apply">Apply</button>
        </div>
        <p class="parameter-apply-message"></p>
      </div>
    `;

    // No submit-type button exists, so pressing Enter in a text field has no
    // implicit-submission target per the HTML form-submission algorithm —
    // Enter deliberately does nothing here (§38 of the M3 mandate); this
    // listener is only a defensive backstop in case a future edit ever adds
    // one.
    container.querySelector("form")?.addEventListener("submit", (event) => event.preventDefault());

    dirtyBadgeEl = container.querySelector<HTMLElement>(".parameter-dirty-badge");
    applyButtonEl = container.querySelector<HTMLButtonElement>('[data-action="apply"]');
    resetButtonEl = container.querySelector<HTMLButtonElement>('[data-action="reset"]');
    applyMessageEl = container.querySelector<HTMLElement>(".parameter-apply-message");
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
    container.querySelector('[data-action="apply"]')?.addEventListener("click", () => {
      void handleApply();
    });

    renderGaugeList();
    updateStatusUI();
  }

  async function load(): Promise<void> {
    renderLoading();
    try {
      const values = await fetchDefaultParameters();
      buildForm(values);
    } catch (error) {
      renderLoadError(isEngineError(error) ? `${error.code}: ${error.message}` : String(error));
    }
  }

  return {
    load,
    getAcceptedRequest: () => (accepted ? buildParametersRequest(accepted) : null),
    getAccepted: () => accepted,
    getApplyStatus: () => applyStatus,
  };
}
