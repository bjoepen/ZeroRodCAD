// Build 023 M2 — the parameter panel DOM component. Owns rendering the
// grouped controls, wiring input events to the local draft
// (parameter_state.ts), and surfacing loading/error/dirty/validation
// feedback. Deliberately does NOT call requestPreviewMeshWithParameters or
// any other preview-regenerating command on edit — M2 is local-editing
// foundation only, M3 connects Apply to the engine (§33/§16 of the M2
// mandate). The DOM tree is built once per successful load and mutated
// surgically afterward (only the changed field's error text / the dirty
// badge / the apply button are touched per keystroke) so typing never loses
// focus or cursor position — a full innerHTML re-render per keystroke would
// break exactly the keyboard usability the mandate calls out.

import { isEngineError } from "./engine";
import {
  groupedParameterFields,
  PARAMETER_FIELDS_BY_KEY,
  type ParameterFieldMeta,
} from "./parameter_metadata";
import { fetchDefaultParameters, type ParametersRequest, type ZeroRodParametersValues } from "./parameters";
import {
  addGauge,
  draftFromValues,
  hasDraftErrors,
  isDraftDirty,
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

export interface ParameterPanelController {
  /** Fetches canonical defaults through the real engine path
   * (parameters_defaults → engine_parameters_defaults) and renders the
   * form. Call once at startup. */
  load: () => Promise<void>;
  /** The last successfully Applied request, or null if Apply has never
   * succeeded this session. Exposed for tests and future M3 wiring — never
   * sent anywhere by M2 itself. */
  getAcceptedRequest: () => ParametersRequest | null;
}

export function createParameterPanelController(container: HTMLElement): ParameterPanelController {
  let draft: ParameterDraftState | null = null;
  let baseline: ZeroRodParametersValues | null = null;
  let acceptedRequest: ParametersRequest | null = null;

  const scalarInputs = new Map<ScalarFieldKey, HTMLInputElement>();
  const scalarErrorEls = new Map<ScalarFieldKey, HTMLElement>();
  let gaugeListEl: HTMLElement | null = null;
  let dirtyBadgeEl: HTMLElement | null = null;
  let applyButtonEl: HTMLButtonElement | null = null;
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

  function updateStatusUI(): void {
    if (!draft || !baseline) return;
    const dirty = isDraftDirty(draft, baseline);
    dirtyBadgeEl?.classList.toggle("is-visible", dirty);
    if (applyButtonEl) {
      applyButtonEl.disabled = hasDraftErrors(draft);
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
    draft = updateScalarField(draft, field, value);
    const errorEl = scalarErrorEls.get(field);
    const errorText = draft.errors[field] ?? "";
    if (errorEl) errorEl.textContent = errorText;
    scalarInputs.get(field)?.setAttribute("aria-invalid", errorText ? "true" : "false");
    updateStatusUI();
  }

  function handleGaugeInput(index: number, value: string): void {
    if (!draft) return;
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
    draft = addGauge(draft);
    renderGaugeList();
    updateStatusUI();
  }

  function handleRemoveGauge(index: number): void {
    if (!draft) return;
    draft = removeGauge(draft, index);
    renderGaugeList();
    updateStatusUI();
  }

  function handleReset(): void {
    if (!baseline) return;
    draft = resetDraft(baseline);
    if (applyMessageEl) {
      applyMessageEl.textContent = "";
      applyMessageEl.classList.remove("is-visible");
    }
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

  function handleApply(): void {
    if (!draft || !applyMessageEl) return;
    const result = serializeDraft(draft);
    applyMessageEl.classList.add("is-visible");
    if (result.ok) {
      acceptedRequest = result.request;
      applyMessageEl.dataset.state = "ok";
      applyMessageEl.textContent =
        "Applied locally. Preview regeneration is not yet connected — that begins in Build 023 M3.";
    } else {
      applyMessageEl.dataset.state = "error";
      applyMessageEl.textContent = `Cannot apply — fix the highlighted fields first (${result.errors.length} issue(s)).`;
    }
  }

  function buildForm(values: ZeroRodParametersValues): void {
    draft = draftFromValues(values);
    baseline = values;
    acceptedRequest = null;
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
          Parameter changes are not yet applied to the preview until the next integration milestone.
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

    container.querySelector("form")?.addEventListener("submit", (event) => event.preventDefault());

    dirtyBadgeEl = container.querySelector<HTMLElement>(".parameter-dirty-badge");
    applyButtonEl = container.querySelector<HTMLButtonElement>('[data-action="apply"]');
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
    container.querySelector('[data-action="apply"]')?.addEventListener("click", handleApply);

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
    getAcceptedRequest: () => acceptedRequest,
  };
}
