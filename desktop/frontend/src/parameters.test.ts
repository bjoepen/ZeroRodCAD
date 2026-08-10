import { beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import {
  buildParametersRequest,
  fetchDefaultParameters,
  PARAMETERS_SCHEMA,
  requestPreviewMeshWithParameters,
  validateParametersShape,
} from "./parameters";

beforeEach(() => {
  invokeMock.mockReset();
});

describe("buildParametersRequest", () => {
  it("wraps a partial value set in the zerorod-parameters/v1 envelope", () => {
    const request = buildParametersRequest({ body_width: 60.0 });
    expect(request).toEqual({ schema: PARAMETERS_SCHEMA, values: { body_width: 60.0 } });
  });

  it("passes an empty value set through unchanged (canonical defaults on the engine side)", () => {
    const request = buildParametersRequest({});
    expect(request).toEqual({ schema: PARAMETERS_SCHEMA, values: {} });
  });
});

describe("validateParametersShape", () => {
  it("accepts a full, well-typed canonical default value set", () => {
    const problems = validateParametersShape({
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
    });
    expect(problems).toEqual([]);
  });

  it("accepts a partial value set (omitted fields are not required here)", () => {
    expect(validateParametersShape({ body_width: 60.0 })).toEqual([]);
  });

  it("accepts an empty value set", () => {
    expect(validateParametersShape({})).toEqual([]);
  });

  it("rejects a non-object payload", () => {
    expect(validateParametersShape("nope")).toEqual(["values must be an object"]);
    expect(validateParametersShape(null)).toEqual(["values must be an object"]);
    expect(validateParametersShape([1, 2, 3])).toEqual(["values must be an object"]);
  });

  it("rejects a wrong-typed numeric field", () => {
    const problems = validateParametersShape({ body_width: "wide" });
    expect(problems).toContain("body_width must be a number");
  });

  it("rejects a wrong-typed project_name", () => {
    const problems = validateParametersShape({ project_name: 123 });
    expect(problems).toContain("project_name must be a string");
  });

  it("rejects a non-array string_gauges_inch", () => {
    const problems = validateParametersShape({ string_gauges_inch: "0.036,0.026" });
    expect(problems).toContain("string_gauges_inch must be an array of numbers");
  });

  it("rejects string_gauges_inch containing a non-number entry", () => {
    const problems = validateParametersShape({ string_gauges_inch: [0.036, "bad"] });
    expect(problems).toContain("string_gauges_inch must be an array of numbers");
  });

  it("does not reject an out-of-range value — that is engine-owned domain validation, not shape", () => {
    // Level 3 (cross-parameter/domain) rules are deliberately not
    // duplicated here — see docs/contracts/ZEROROD-PARAMETERS-V1.md.
    expect(validateParametersShape({ body_width: -1.0 })).toEqual([]);
  });
});

describe("fetchDefaultParameters", () => {
  it("returns the values object from the engine_parameters_defaults command", async () => {
    invokeMock.mockResolvedValueOnce({
      schema: PARAMETERS_SCHEMA,
      values: { body_width: 38.0, string_gauges_inch: [0.036, 0.026, 0.017] },
    });
    const values = await fetchDefaultParameters();
    expect(values.body_width).toBe(38.0);
    expect(invokeMock).toHaveBeenCalledWith("engine_parameters_defaults");
  });
});

describe("requestPreviewMeshWithParameters", () => {
  it("invokes engine_preview_mesh_with_parameters with a wrapped parameters envelope", async () => {
    invokeMock.mockResolvedValueOnce({ schema: "zerorod-mesh/v1", meshes: [], lines: [] });
    await requestPreviewMeshWithParameters({ body_width: 60.0 });
    expect(invokeMock).toHaveBeenCalledWith("engine_preview_mesh_with_parameters", {
      parameters: { schema: PARAMETERS_SCHEMA, values: { body_width: 60.0 } },
    });
  });
});
