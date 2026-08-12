import { describe, expect, it } from "vitest";
import {
  GROUP_ORDER,
  groupedParameterFields,
  PARAMETER_FIELDS,
  PARAMETER_FIELDS_BY_KEY,
} from "./parameter_metadata";

// Exact field order from docs/contracts/ZEROROD-PARAMETERS-V1.md's field
// table (== ZeroRodParameters.to_dict() shape) — the single source of
// truth this metadata module presents, never a UI-invented set.
const CONTRACT_FIELDS = [
  "project_name",
  "body_width",
  "body_depth",
  "fretboard_height",
  "rod_diameter",
  "groove_diameter",
  "rod_center_z_offset",
  "groove_front_clearance",
  "string_gauges_inch",
  "string_spacing",
  "string_inlet_y",
  "string_inlet_z",
  "channel_diameter",
  "channel_overrun_at_inlet",
  "channel_rod_clearance",
  "minimum_wall",
];

describe("PARAMETER_FIELDS", () => {
  it("covers exactly the 16 zerorod-parameters/v1 fields, in contract order", () => {
    expect(PARAMETER_FIELDS.map((meta) => meta.field)).toEqual(CONTRACT_FIELDS);
  });

  it("treats only project_name as metadata (not geometry-affecting)", () => {
    const metadataFields = PARAMETER_FIELDS.filter((meta) => meta.isMetadata).map((meta) => meta.field);
    expect(metadataFields).toEqual(["project_name"]);
  });

  it("uses mm for every geometry field, inch for string_gauges_inch, none for project_name", () => {
    for (const meta of PARAMETER_FIELDS) {
      if (meta.field === "project_name") {
        expect(meta.unit).toBe("");
      } else if (meta.field === "string_gauges_inch") {
        expect(meta.unit).toBe("in");
      } else {
        expect(meta.unit).toBe("mm");
      }
    }
  });

  it("gives project_name a text control, string_gauges_inch a gauge-array control, everything else numeric", () => {
    expect(PARAMETER_FIELDS_BY_KEY.project_name.kind).toBe("text");
    expect(PARAMETER_FIELDS_BY_KEY.string_gauges_inch.kind).toBe("gauge-array");
    for (const meta of PARAMETER_FIELDS) {
      if (meta.field === "project_name" || meta.field === "string_gauges_inch") continue;
      expect(meta.kind).toBe("number");
    }
  });

  it("only marks positiveOnly for fields the contract documents a '> 0' constraint for", () => {
    const positiveFields = PARAMETER_FIELDS.filter((meta) => meta.positiveOnly).map((meta) => meta.field);
    expect(new Set(positiveFields)).toEqual(
      new Set([
        "body_width",
        "body_depth",
        "fretboard_height",
        "rod_diameter",
        "groove_diameter",
        "string_gauges_inch",
        "channel_diameter",
      ]),
    );
  });

  it("assigns every field to one of the declared groups", () => {
    for (const meta of PARAMETER_FIELDS) {
      expect(GROUP_ORDER).toContain(meta.group);
    }
  });
});

describe("groupedParameterFields", () => {
  it("returns every contract field exactly once across all groups", () => {
    const grouped = groupedParameterFields();
    const allFields = grouped.flatMap((entry) => entry.fields.map((meta) => meta.field));
    expect([...allFields].sort()).toEqual([...CONTRACT_FIELDS].sort());
  });

  it("follows GROUP_ORDER and omits empty groups", () => {
    const grouped = groupedParameterFields();
    const groupNames = grouped.map((entry) => entry.group);
    const expectedOrder = GROUP_ORDER.filter((group) => groupNames.includes(group));
    expect(groupNames).toEqual(expectedOrder);
    for (const entry of grouped) {
      expect(entry.fields.length).toBeGreaterThan(0);
    }
  });

  it("puts project_name alone in the Project group", () => {
    const grouped = groupedParameterFields();
    const projectGroup = grouped.find((entry) => entry.group === "Project");
    expect(projectGroup?.fields.map((meta) => meta.field)).toEqual(["project_name"]);
  });
});
