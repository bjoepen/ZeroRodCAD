import { beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import { PARAMETERS_SCHEMA, type ZeroRodParametersValues } from "./parameters";
import {
  requestProjectOpen,
  requestProjectSave,
  selectProjectOpenFile,
  selectProjectSaveFile,
} from "./project";

const VALUES: ZeroRodParametersValues = {
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

beforeEach(() => {
  invokeMock.mockReset();
});

describe("selectProjectOpenFile", () => {
  it("invokes select_project_open_file and returns the chosen path", async () => {
    invokeMock.mockResolvedValueOnce("/Users/example/projects/cbg-open-g.zerorod");
    const path = await selectProjectOpenFile();
    expect(path).toBe("/Users/example/projects/cbg-open-g.zerorod");
    expect(invokeMock).toHaveBeenCalledWith("select_project_open_file");
  });

  it("returns null on cancellation without throwing", async () => {
    invokeMock.mockResolvedValueOnce(null);
    const path = await selectProjectOpenFile();
    expect(path).toBeNull();
  });
});

describe("selectProjectSaveFile", () => {
  it("invokes select_project_save_file with the default filename", async () => {
    invokeMock.mockResolvedValueOnce("/Users/example/projects/cbg-open-g.zerorod");
    const path = await selectProjectSaveFile("cbg-open-g.zerorod");
    expect(path).toBe("/Users/example/projects/cbg-open-g.zerorod");
    expect(invokeMock).toHaveBeenCalledWith("select_project_save_file", {
      default_file_name: "cbg-open-g.zerorod",
    });
  });

  it("returns null on cancellation without throwing", async () => {
    invokeMock.mockResolvedValueOnce(null);
    const path = await selectProjectSaveFile("cbg-open-g.zerorod");
    expect(path).toBeNull();
  });
});

describe("requestProjectOpen", () => {
  it("invokes engine_project_open with the given path and returns the loaded values", async () => {
    invokeMock.mockResolvedValueOnce({ schema: PARAMETERS_SCHEMA, values: VALUES });

    const result = await requestProjectOpen("/Users/example/projects/cbg-open-g.zerorod");

    expect(result.values).toEqual(VALUES);
    expect(invokeMock).toHaveBeenCalledWith("engine_project_open", {
      path: "/Users/example/projects/cbg-open-g.zerorod",
    });
  });

  it("propagates a rejected invoke() call (structured EngineError) unchanged", async () => {
    const engineError = { code: "project_not_found", message: "not found" };
    invokeMock.mockRejectedValueOnce(engineError);

    await expect(requestProjectOpen("/nowhere.zerorod")).rejects.toEqual(engineError);
  });
});

describe("requestProjectSave", () => {
  it("invokes engine_project_save with a wrapped parameters envelope and the destination path", async () => {
    invokeMock.mockResolvedValueOnce({ path: "/Users/example/projects/cbg-open-g.zerorod" });

    const result = await requestProjectSave(VALUES, "/Users/example/projects/cbg-open-g.zerorod");

    expect(result.path).toBe("/Users/example/projects/cbg-open-g.zerorod");
    expect(invokeMock).toHaveBeenCalledWith("engine_project_save", {
      parameters: { schema: PARAMETERS_SCHEMA, values: VALUES },
      path: "/Users/example/projects/cbg-open-g.zerorod",
    });
  });

  it("propagates a rejected invoke() call (structured EngineError) unchanged", async () => {
    const engineError = { code: "project_permission_denied", message: "denied" };
    invokeMock.mockRejectedValueOnce(engineError);

    await expect(requestProjectSave(VALUES, "/readonly/x.zerorod")).rejects.toEqual(engineError);
  });
});
