// Build 023 M2 — local parameter draft state. Purely local: nothing here
// ever calls invoke() or talks to the sidecar (that stays parameters.ts's
// job, unused by this milestone's UI). Owns:
//   - the local "draft" a.k.a. "what's currently in the form controls"
//   - dirty tracking (draft vs. the loaded/accepted baseline)
//   - local structural validation (required/finite/positive-per-contract —
//     never cross-parameter/domain rules, which stay engine-owned)
//   - serialization to a zerorod-parameters/v1 request, blocked while any
//     field is invalid
//
// Every mutator is pure (old state in, new state out) so it's trivial to
// unit test and so parameter_panel.ts can re-render from a single new
// state value per edit, no hidden mutation.

import {
  buildParametersRequest,
  validateParametersShape,
  type ParametersRequest,
  type ZeroRodParametersValues,
} from "./parameters";
import { PARAMETER_FIELDS_BY_KEY } from "./parameter_metadata";

export type ScalarFieldKey = Exclude<keyof ZeroRodParametersValues, "string_gauges_inch">;

export const SCALAR_FIELDS: readonly ScalarFieldKey[] = [
  "project_name",
  "body_width",
  "body_depth",
  "fretboard_height",
  "rod_diameter",
  "groove_diameter",
  "rod_center_z_offset",
  "groove_front_clearance",
  "string_spacing",
  "string_inlet_y",
  "string_inlet_z",
  "channel_diameter",
  "channel_overrun_at_inlet",
  "channel_rod_clearance",
  "minimum_wall",
];

export interface ParameterDraftState {
  /** Last known-valid typed values — what would be serialized right now if
   * every field were valid. Fields with a currently-invalid `raw` entry
   * keep their previous valid value here (never NaN/Infinity/null). */
  values: ZeroRodParametersValues;
  /** Exact text currently in each scalar control, including invalid text —
   * this is what the DOM input shows. */
  raw: Record<ScalarFieldKey, string>;
  rawGauges: string[];
  errors: Partial<Record<ScalarFieldKey, string>>;
  gaugeErrors: (string | null)[];
}

function cloneValues(values: ZeroRodParametersValues): ZeroRodParametersValues {
  return { ...values, string_gauges_inch: [...values.string_gauges_inch] };
}

/** Canonical string form used both to seed `raw`/`rawGauges` and to detect
 * dirtiness against a baseline — one formatting function, one source of
 * truth, so "freshly loaded" always reads as raw === formatted(baseline). */
export function formatFieldValue(value: string | number): string {
  return typeof value === "string" ? value : String(value);
}

export function draftFromValues(values: ZeroRodParametersValues): ParameterDraftState {
  const raw = {} as Record<ScalarFieldKey, string>;
  for (const field of SCALAR_FIELDS) {
    raw[field] = formatFieldValue(values[field] as string | number);
  }
  return {
    values: cloneValues(values),
    raw,
    rawGauges: values.string_gauges_inch.map((gauge) => String(gauge)),
    errors: {},
    gaugeErrors: values.string_gauges_inch.map(() => null),
  };
}

/** Reset is just re-deriving a fresh draft from the canonical defaults —
 * no separate hardcoded reset path (§17 of the M2 mandate). */
export function resetDraft(defaults: ZeroRodParametersValues): ParameterDraftState {
  return draftFromValues(defaults);
}

function parseNumericField(field: ScalarFieldKey, rawInput: string): string | null {
  const meta = PARAMETER_FIELDS_BY_KEY[field];
  const trimmed = rawInput.trim();
  if (trimmed === "") {
    return `${meta.label} is required.`;
  }
  const value = Number(trimmed);
  if (Number.isNaN(value) || !Number.isFinite(value)) {
    return `${meta.label} must be a finite number.`;
  }
  if (meta.positiveOnly && !(value > 0)) {
    return `${meta.label} must be greater than 0.`;
  }
  return null;
}

/** Updates one scalar (non-gauge) field from raw control text. Only writes
 * to `values` when the new text parses cleanly — an invalid edit is visible
 * in `raw`/`errors` but never reaches `values`, so `values` is always a
 * contract-safe snapshot (§35 of the M2 mandate: invalid input must never
 * become a valid contract value). */
export function updateScalarField(
  draft: ParameterDraftState,
  field: ScalarFieldKey,
  rawInput: string,
): ParameterDraftState {
  const values = cloneValues(draft.values);
  const raw = { ...draft.raw, [field]: rawInput };
  const errors = { ...draft.errors };

  if (field === "project_name") {
    if (rawInput.trim() === "") {
      errors.project_name = "Project name is required.";
    } else {
      delete errors.project_name;
      values.project_name = rawInput;
    }
    return { ...draft, values, raw, errors };
  }

  const problem = parseNumericField(field, rawInput);
  if (problem) {
    errors[field] = problem;
  } else {
    delete errors[field];
    (values as unknown as Record<ScalarFieldKey, number>)[field] = Number(rawInput.trim());
  }
  return { ...draft, values, raw, errors };
}

function parseGaugeValue(rawInput: string): { value: number | null; error: string | null } {
  const trimmed = rawInput.trim();
  if (trimmed === "") {
    return { value: null, error: "String gauge is required." };
  }
  const value = Number(trimmed);
  if (Number.isNaN(value) || !Number.isFinite(value)) {
    return { value: null, error: "String gauge must be a finite number." };
  }
  if (!(value > 0)) {
    return { value: null, error: "String gauge must be greater than 0." };
  }
  return { value, error: null };
}

export function updateGauge(
  draft: ParameterDraftState,
  index: number,
  rawInput: string,
): ParameterDraftState {
  const values = cloneValues(draft.values);
  const rawGauges = [...draft.rawGauges];
  const gaugeErrors = [...draft.gaugeErrors];
  rawGauges[index] = rawInput;

  const { value, error } = parseGaugeValue(rawInput);
  gaugeErrors[index] = error;
  if (value !== null) {
    values.string_gauges_inch[index] = value;
  }
  return { ...draft, values, rawGauges, gaugeErrors };
}

/** Appends a new (initially empty/invalid) gauge entry — order is
 * significant (engine semantics), so it is always appended at the end,
 * never auto-sorted (§22 of the M2 mandate). */
export function addGauge(draft: ParameterDraftState): ParameterDraftState {
  const values = cloneValues(draft.values);
  values.string_gauges_inch.push(0);
  return {
    ...draft,
    values,
    rawGauges: [...draft.rawGauges, ""],
    gaugeErrors: [...draft.gaugeErrors, "String gauge is required."],
  };
}

/** No-op if only one gauge remains — the contract requires at least one
 * entry (docs/contracts/ZEROROD-PARAMETERS-V1.md), so the UI never lets the
 * draft reach zero entries rather than surfacing a synthetic error for it. */
export function removeGauge(draft: ParameterDraftState, index: number): ParameterDraftState {
  if (draft.rawGauges.length <= 1) {
    return draft;
  }
  const values = cloneValues(draft.values);
  values.string_gauges_inch.splice(index, 1);
  const rawGauges = [...draft.rawGauges];
  rawGauges.splice(index, 1);
  const gaugeErrors = [...draft.gaugeErrors];
  gaugeErrors.splice(index, 1);
  return { ...draft, values, rawGauges, gaugeErrors };
}

/** Dirty means "the text currently in the form differs from the
 * loaded/accepted baseline" — including an invalid in-progress edit, which
 * is deliberately still "modified" even though it hasn't reached `values`
 * yet (§18 of the M2 mandate). */
export function isDraftDirty(draft: ParameterDraftState, baseline: ZeroRodParametersValues): boolean {
  for (const field of SCALAR_FIELDS) {
    if (draft.raw[field] !== formatFieldValue(baseline[field] as string | number)) {
      return true;
    }
  }
  if (draft.rawGauges.length !== baseline.string_gauges_inch.length) {
    return true;
  }
  for (let i = 0; i < draft.rawGauges.length; i++) {
    if (draft.rawGauges[i] !== String(baseline.string_gauges_inch[i])) {
      return true;
    }
  }
  return false;
}

export function hasDraftErrors(draft: ParameterDraftState): boolean {
  return Object.values(draft.errors).some(Boolean) || draft.gaugeErrors.some((error) => error !== null);
}

function collectDraftErrors(draft: ParameterDraftState): string[] {
  return [
    ...Object.values(draft.errors).filter((error): error is string => Boolean(error)),
    ...draft.gaugeErrors.filter((error): error is string => error !== null),
  ];
}

export type DraftSerializationResult =
  | { ok: true; request: ParametersRequest }
  | { ok: false; errors: string[] };

/** Serializes the draft to a zerorod-parameters/v1 request — but only when
 * every field is currently valid (§34/§35 of the M2 mandate: a draft with
 * any invalid field must never produce a request, not even with the stale
 * last-valid `values`). Never sent anywhere by this milestone's UI — proving
 * the shape is valid is the whole of M2's scope here. */
export function serializeDraft(draft: ParameterDraftState): DraftSerializationResult {
  if (hasDraftErrors(draft)) {
    return { ok: false, errors: collectDraftErrors(draft) };
  }
  const shapeProblems = validateParametersShape(draft.values);
  if (shapeProblems.length > 0) {
    return { ok: false, errors: shapeProblems };
  }
  return { ok: true, request: buildParametersRequest(draft.values) };
}
