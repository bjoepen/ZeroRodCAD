import { describe, expect, it } from "vitest";
import type { ZeroRodParametersValues } from "./parameters";
import {
  addGauge,
  draftFromValues,
  hasDraftErrors,
  isDraftDirty,
  isGeometryUnchanged,
  removeGauge,
  resetDraft,
  serializeDraft,
  updateGauge,
  updateScalarField,
  valuesEqual,
} from "./parameter_state";

// Canonical defaults exactly as documented in
// docs/contracts/ZEROROD-PARAMETERS-V1.md — used as a realistic baseline
// throughout, not a UI-invented value set.
const DEFAULTS: ZeroRodParametersValues = {
  project_name: "CBG Open G",
  body_width: 38.0,
  body_depth: 9.0,
  fretboard_height: 6.9,
  rod_diameter: 3.0,
  groove_diameter: 2.94,
  rod_center_z_offset: -0.75,
  groove_front_clearance: 0.01,
  string_gauges_inch: [0.036, 0.026, 0.017],
  string_spacing: 10.0,
  string_inlet_y: 0.0,
  string_inlet_z: 2.8,
  channel_diameter: 1.15,
  channel_overrun_at_inlet: 0.8,
  channel_rod_clearance: 0.05,
  minimum_wall: 1.2,
};

describe("draftFromValues", () => {
  it("seeds raw text that round-trips the given values and is not dirty against them", () => {
    const draft = draftFromValues(DEFAULTS);
    expect(draft.raw.body_width).toBe("38");
    expect(draft.raw.project_name).toBe("CBG Open G");
    expect(draft.rawGauges).toEqual(["0.036", "0.026", "0.017"]);
    expect(isDraftDirty(draft, DEFAULTS)).toBe(false);
    expect(hasDraftErrors(draft)).toBe(false);
  });
});

describe("updateScalarField", () => {
  it("accepts a valid number and updates values, clearing any error", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "60");
    expect(draft.values.body_width).toBe(60);
    expect(draft.errors.body_width).toBeUndefined();
  });

  it("rejects non-numeric text without touching the committed value", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "wide");
    expect(draft.values.body_width).toBe(38.0);
    expect(draft.errors.body_width).toMatch(/finite number/);
  });

  it("rejects NaN", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "NaN");
    expect(draft.values.body_width).toBe(38.0);
    expect(draft.errors.body_width).toMatch(/finite number/);
  });

  it("rejects Infinity", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "Infinity");
    expect(draft.values.body_width).toBe(38.0);
    expect(draft.errors.body_width).toMatch(/finite number/);
  });

  it("rejects -Infinity", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "rod_center_z_offset", "-Infinity");
    expect(draft.values.rod_center_z_offset).toBe(-0.75);
    expect(draft.errors.rod_center_z_offset).toMatch(/finite number/);
  });

  it("rejects an empty value as required", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "");
    expect(draft.errors.body_width).toMatch(/required/);
  });

  it("rejects zero/negative for a contract-documented positive-only field", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "rod_diameter", "0");
    expect(draft.errors.rod_diameter).toMatch(/greater than 0/);
    expect(draft.values.rod_diameter).toBe(3.0);
  });

  it("allows a negative value for a field with no positive-only constraint", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "rod_center_z_offset", "-5.5");
    expect(draft.errors.rod_center_z_offset).toBeUndefined();
    expect(draft.values.rod_center_z_offset).toBe(-5.5);
  });

  it("clears the error once the value is corrected", () => {
    let draft = draftFromValues(DEFAULTS);
    draft = updateScalarField(draft, "body_width", "abc");
    expect(draft.errors.body_width).toBeDefined();
    draft = updateScalarField(draft, "body_width", "45.5");
    expect(draft.errors.body_width).toBeUndefined();
    expect(draft.values.body_width).toBe(45.5);
  });

  it("updates project_name as plain text", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "project_name", "My Rod");
    expect(draft.values.project_name).toBe("My Rod");
    expect(draft.errors.project_name).toBeUndefined();
  });

  it("rejects an empty project_name", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "project_name", "   ");
    expect(draft.errors.project_name).toMatch(/required/);
  });
});

describe("updateGauge / addGauge / removeGauge", () => {
  it("accepts a valid gauge edit", () => {
    const draft = updateGauge(draftFromValues(DEFAULTS), 0, "0.042");
    expect(draft.values.string_gauges_inch[0]).toBe(0.042);
    expect(draft.gaugeErrors[0]).toBeNull();
  });

  it("rejects a non-positive gauge, keeping the old value", () => {
    const draft = updateGauge(draftFromValues(DEFAULTS), 0, "-1");
    expect(draft.values.string_gauges_inch[0]).toBe(0.036);
    expect(draft.gaugeErrors[0]).toMatch(/greater than 0/);
  });

  it("rejects NaN/Infinity gauge text", () => {
    const nanDraft = updateGauge(draftFromValues(DEFAULTS), 0, "NaN");
    expect(nanDraft.gaugeErrors[0]).toMatch(/finite number/);
    const infDraft = updateGauge(draftFromValues(DEFAULTS), 0, "Infinity");
    expect(infDraft.gaugeErrors[0]).toMatch(/finite number/);
  });

  it("clears a gauge error after correction", () => {
    let draft = updateGauge(draftFromValues(DEFAULTS), 1, "bad");
    expect(draft.gaugeErrors[1]).toBeDefined();
    draft = updateGauge(draft, 1, "0.030");
    expect(draft.gaugeErrors[1]).toBeNull();
    expect(draft.values.string_gauges_inch[1]).toBe(0.03);
  });

  it("appends a new gauge entry at the end, initially invalid (required)", () => {
    const draft = addGauge(draftFromValues(DEFAULTS));
    expect(draft.rawGauges).toEqual(["0.036", "0.026", "0.017", ""]);
    expect(draft.gaugeErrors[3]).toMatch(/required/);
  });

  it("removes a gauge entry by index, preserving order of the rest", () => {
    const draft = removeGauge(draftFromValues(DEFAULTS), 1);
    expect(draft.rawGauges).toEqual(["0.036", "0.017"]);
    expect(draft.values.string_gauges_inch).toEqual([0.036, 0.017]);
  });

  it("refuses to remove the last remaining gauge (contract requires at least one)", () => {
    let draft = draftFromValues(DEFAULTS);
    draft = removeGauge(draft, 0);
    draft = removeGauge(draft, 0);
    expect(draft.rawGauges).toHaveLength(1);
    const unchanged = removeGauge(draft, 0);
    expect(unchanged.rawGauges).toHaveLength(1);
    expect(unchanged).toEqual(draft);
  });
});

describe("isDraftDirty", () => {
  it("is false for a freshly loaded draft", () => {
    expect(isDraftDirty(draftFromValues(DEFAULTS), DEFAULTS)).toBe(false);
  });

  it("is true after a valid scalar edit", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "60");
    expect(isDraftDirty(draft, DEFAULTS)).toBe(true);
  });

  it("is true even while the edit is still invalid (in-progress typing counts as modified)", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "abc");
    expect(isDraftDirty(draft, DEFAULTS)).toBe(true);
  });

  it("is true after a gauge edit", () => {
    const draft = updateGauge(draftFromValues(DEFAULTS), 0, "0.048");
    expect(isDraftDirty(draft, DEFAULTS)).toBe(true);
  });
});

describe("resetDraft", () => {
  it("restores exactly the given canonical defaults and clears dirty state", () => {
    let draft = draftFromValues(DEFAULTS);
    draft = updateScalarField(draft, "body_width", "99");
    draft = updateGauge(draft, 0, "0.099");
    expect(isDraftDirty(draft, DEFAULTS)).toBe(true);

    draft = resetDraft(DEFAULTS);
    expect(draft.values).toEqual(DEFAULTS);
    expect(isDraftDirty(draft, DEFAULTS)).toBe(false);
    expect(hasDraftErrors(draft)).toBe(false);
  });

  it("clears prior field errors", () => {
    let draft = draftFromValues(DEFAULTS);
    draft = updateScalarField(draft, "body_width", "abc");
    expect(hasDraftErrors(draft)).toBe(true);
    draft = resetDraft(DEFAULTS);
    expect(hasDraftErrors(draft)).toBe(false);
  });
});

describe("serializeDraft", () => {
  it("serializes a fully valid draft to a zerorod-parameters/v1 request", () => {
    const draft = draftFromValues(DEFAULTS);
    const result = serializeDraft(draft);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.request.schema).toBe("zerorod-parameters/v1");
      expect(result.request.values).toEqual(DEFAULTS);
    }
  });

  it("reflects a valid edit in the serialized request", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "60");
    const result = serializeDraft(draft);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.request.values.body_width).toBe(60);
    }
  });

  it("refuses to serialize a draft with an invalid scalar field", () => {
    const draft = updateScalarField(draftFromValues(DEFAULTS), "body_width", "abc");
    const result = serializeDraft(draft);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.length).toBeGreaterThan(0);
    }
  });

  it("refuses to serialize a draft with an invalid gauge entry", () => {
    const draft = updateGauge(draftFromValues(DEFAULTS), 0, "NaN");
    const result = serializeDraft(draft);
    expect(result.ok).toBe(false);
  });

  it("never lets NaN or Infinity reach a serialized request", () => {
    let draft = draftFromValues(DEFAULTS);
    draft = updateScalarField(draft, "body_width", "NaN");
    expect(serializeDraft(draft).ok).toBe(false);
    draft = updateScalarField(draft, "body_width", "Infinity");
    expect(serializeDraft(draft).ok).toBe(false);
  });
});

describe("isGeometryUnchanged", () => {
  it("is true for identical values", () => {
    expect(isGeometryUnchanged(DEFAULTS, DEFAULTS)).toBe(true);
  });

  it("is true when only project_name differs", () => {
    const other = { ...DEFAULTS, project_name: "Something Else" };
    expect(isGeometryUnchanged(DEFAULTS, other)).toBe(true);
  });

  it("is false when a geometry field differs", () => {
    const other = { ...DEFAULTS, body_width: 60 };
    expect(isGeometryUnchanged(DEFAULTS, other)).toBe(false);
  });

  it("is false when string_gauges_inch differs", () => {
    const other = { ...DEFAULTS, string_gauges_inch: [0.036, 0.048, 0.017] };
    expect(isGeometryUnchanged(DEFAULTS, other)).toBe(false);
  });

  it("is false when string_gauges_inch length differs", () => {
    const other = { ...DEFAULTS, string_gauges_inch: [0.036, 0.026] };
    expect(isGeometryUnchanged(DEFAULTS, other)).toBe(false);
  });
});

describe("valuesEqual", () => {
  it("is true for identical values", () => {
    expect(valuesEqual(DEFAULTS, DEFAULTS)).toBe(true);
  });

  it("is false when only project_name differs (unlike isGeometryUnchanged)", () => {
    const other = { ...DEFAULTS, project_name: "Something Else" };
    expect(valuesEqual(DEFAULTS, other)).toBe(false);
    expect(isGeometryUnchanged(DEFAULTS, other)).toBe(true);
  });

  it("is false when a geometry field differs", () => {
    const other = { ...DEFAULTS, body_width: 60 };
    expect(valuesEqual(DEFAULTS, other)).toBe(false);
  });
});
