// Build 023 M2 — UI-only metadata for the canonical zerorod-parameters/v1
// fields (parameters.ts's ZeroRodParametersValues). This is a presentation
// layer, not a second parameter model: field names, units, and the
// single-field "> 0" constraints below are all copied verbatim from
// docs/contracts/ZEROROD-PARAMETERS-V1.md's field table — never invented.
// Cross-parameter/domain rules (groove < rod, string-spacing feasibility,
// channel clearance feasibility) are deliberately NOT represented here;
// those stay engine-only (zerorodcad.validation.validate_parameters),
// per the mandate's single-source-of-truth requirement.

import type { ZeroRodParametersValues } from "./parameters";

export type ParameterGroupName =
  | "Project"
  | "Body"
  | "Rod & Groove"
  | "Strings"
  | "Channel"
  | "Tolerances";

/** Declared render order — grouping follows the contract's own field-name
 * prefixes (body_, rod_/groove_, string_, channel_), not an invented
 * taxonomy. */
export const GROUP_ORDER: readonly ParameterGroupName[] = [
  "Project",
  "Body",
  "Rod & Groove",
  "Strings",
  "Channel",
  "Tolerances",
];

export type ParameterControlKind = "text" | "number" | "gauge-array";

export interface ParameterFieldMeta {
  field: keyof ZeroRodParametersValues;
  label: string;
  group: ParameterGroupName;
  /** Empty string when the field has no unit (project_name). */
  unit: string;
  kind: ParameterControlKind;
  /** project_name only — metadata, not geometry-affecting (§23 of the M2
   * mandate). Edits to metadata fields carry the same "not applied to
   * preview yet" caveat as geometry fields in M2, but M3/M4 may later treat
   * them differently (metadata edits need not trigger regeneration). */
  isMetadata: boolean;
  /** Reuses the contract's own documented "> 0" constraint for this field
   * (see docs/contracts/ZEROROD-PARAMETERS-V1.md). A single-field bound the
   * contract states directly — not a UI-invented range. Cross-parameter
   * rules stay engine-only. */
  positiveOnly: boolean;
  description: string;
}

export const PARAMETER_FIELDS: readonly ParameterFieldMeta[] = [
  {
    field: "project_name",
    label: "Project Name",
    group: "Project",
    unit: "",
    kind: "text",
    isMetadata: true,
    positiveOnly: false,
    description: "Metadata only — not geometry-affecting.",
  },
  {
    field: "body_width",
    label: "Body Width",
    group: "Body",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: true,
    description: "Overall body width.",
  },
  {
    field: "body_depth",
    label: "Body Depth",
    group: "Body",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: true,
    description: "Overall body depth.",
  },
  {
    field: "fretboard_height",
    label: "Fretboard Height",
    group: "Body",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: true,
    description: "Fretboard height above the body.",
  },
  {
    field: "rod_diameter",
    label: "Rod Diameter",
    group: "Rod & Groove",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: true,
    description: "Diameter of the rod.",
  },
  {
    field: "groove_diameter",
    label: "Groove Diameter",
    group: "Rod & Groove",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: true,
    description: "Diameter of the groove (must stay smaller than the rod diameter — checked engine-side).",
  },
  {
    field: "rod_center_z_offset",
    label: "Rod Center Z Offset",
    group: "Rod & Groove",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Z offset of the rod center.",
  },
  {
    field: "groove_front_clearance",
    label: "Groove Front Clearance",
    group: "Rod & Groove",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Clearance at the front of the groove.",
  },
  {
    field: "string_gauges_inch",
    label: "String Gauges",
    group: "Strings",
    unit: "in",
    kind: "gauge-array",
    isMetadata: false,
    positiveOnly: true,
    description: "One entry per string, in order. At least one entry required.",
  },
  {
    field: "string_spacing",
    label: "String Spacing",
    group: "Strings",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Spacing between adjacent strings.",
  },
  {
    field: "string_inlet_y",
    label: "String Inlet Y",
    group: "Strings",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Y position of the string inlet point.",
  },
  {
    field: "string_inlet_z",
    label: "String Inlet Z",
    group: "Strings",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Z position of the string inlet point.",
  },
  {
    field: "channel_diameter",
    label: "Channel Diameter",
    group: "Channel",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: true,
    description: "Diameter of the string channel.",
  },
  {
    field: "channel_overrun_at_inlet",
    label: "Channel Overrun At Inlet",
    group: "Channel",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Channel overrun length at the inlet.",
  },
  {
    field: "channel_rod_clearance",
    label: "Channel Rod Clearance",
    group: "Channel",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Clearance between the channel and the rod.",
  },
  {
    field: "minimum_wall",
    label: "Minimum Wall",
    group: "Tolerances",
    unit: "mm",
    kind: "number",
    isMetadata: false,
    positiveOnly: false,
    description: "Minimum wall thickness used by the string-spacing feasibility rule (validation-only, no effect on generated solids).",
  },
];

export const PARAMETER_FIELDS_BY_KEY: Readonly<
  Record<keyof ZeroRodParametersValues, ParameterFieldMeta>
> = Object.fromEntries(PARAMETER_FIELDS.map((meta) => [meta.field, meta])) as Record<
  keyof ZeroRodParametersValues,
  ParameterFieldMeta
>;

/** Groups PARAMETER_FIELDS by GROUP_ORDER, omitting empty groups. */
export function groupedParameterFields(): { group: ParameterGroupName; fields: ParameterFieldMeta[] }[] {
  return GROUP_ORDER.map((group) => ({
    group,
    fields: PARAMETER_FIELDS.filter((meta) => meta.group === group),
  })).filter((entry) => entry.fields.length > 0);
}
