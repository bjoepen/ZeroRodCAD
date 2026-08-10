// Build 023 M2 — local parameter draft state; extended in M3 with
// `cloneValues`/`isGeometryUnchanged` for the accepted-state Apply flow
// (parameter_panel.ts). Still purely local: nothing here ever calls
// invoke() or talks to the sidecar (that stays parameters.ts's job — the
// actual request happens in preview.ts, triggered by parameter_panel.ts's
// Apply handler, not from this module). Owns:
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

export function cloneValues(values: ZeroRodParametersValues): ZeroRodParametersValues {
  return { ...values, string_gauges_inch: [...values.string_gauges_inch] };
}

/** True when every geometry-affecting field (everything except the
 * `project_name` metadata field) is identical between `a` and `b` — used by
 * Build 023 M3's Apply flow to skip the engine round trip entirely for a
 * metadata-only change (§24 of the M3 mandate), since a request that only
 * differs in `project_name` cannot produce a different mesh. */
export function isGeometryUnchanged(a: ZeroRodParametersValues, b: ZeroRodParametersValues): boolean {
  for (const field of SCALAR_FIELDS) {
    if (field === "project_name") continue;
    if (a[field] !== b[field]) return false;
  }
  if (a.string_gauges_inch.length !== b.string_gauges_inch.length) return false;
  for (let i = 0; i < a.string_gauges_inch.length; i++) {
    if (a.string_gauges_inch[i] !== b.string_gauges_inch[i]) return false;
  }
  return true;
}

/** Full field-for-field equality, including `project_name` — unlike
 * `isGeometryUnchanged`. Build 023 M4 uses this as the live-preview
 * scheduler's dedup check (live_preview.ts's `isEqual` config): it only
 * needs to recognize "this is literally the same request I already
 * dispatched," not to distinguish metadata from geometry — that
 * distinction is made earlier, at the call site, via `isGeometryUnchanged`
 * gating whether to schedule anything at all. */
export function valuesEqual(a: ZeroRodParametersValues, b: ZeroRodParametersValues): boolean {
  return a.project_name === b.project_name && isGeometryUnchanged(a, b);
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

/** Dirty means "the text currently in the form differs from `baseline`" —
 * including an invalid in-progress edit, which is deliberately still
 * "modified" even though it hasn't reached `values` yet (§18 of the M2
 * mandate). The caller decides what `baseline` means: M2 passed the loaded
 * canonical defaults; Build 023 M3 instead passes the last successfully
 * *accepted* parameter state (§26 of the M3 mandate — dirty means "differs
 * from the last applied state," not "differs from startup defaults"). This
 * function itself is unchanged between M2 and M3; only what callers pass in
 * differs. */
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
