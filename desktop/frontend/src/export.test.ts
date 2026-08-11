import { beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import { PARAMETERS_SCHEMA } from "./parameters";
import { requestExport, selectExportDirectory, type ExportResult } from "./export";

beforeEach(() => {
  invokeMock.mockReset();
});

describe("selectExportDirectory", () => {
  it("invokes select_export_directory and returns the chosen path", async () => {
    invokeMock.mockResolvedValueOnce("/Users/example/exports");
    const path = await selectExportDirectory();
    expect(path).toBe("/Users/example/exports");
    expect(invokeMock).toHaveBeenCalledWith("select_export_directory");
  });

  it("returns null on cancellation without throwing", async () => {
    invokeMock.mockResolvedValueOnce(null);
    const path = await selectExportDirectory();
    expect(path).toBeNull();
  });
});

describe("requestExport", () => {
  it("invokes engine_export with a wrapped parameters envelope and the destination", async () => {
    const result: ExportResult = {
      output_directory: "/Users/example/exports",
      files: [
        { role: "body_stl", filename: "cbg-open-g-body.stl", path: "/Users/example/exports/cbg-open-g-body.stl" },
        {
          role: "assembly_step",
          filename: "cbg-open-g-assembly.step",
          path: "/Users/example/exports/cbg-open-g-assembly.step",
        },
        {
          role: "report_markdown",
          filename: "cbg-open-g-report.md",
          path: "/Users/example/exports/cbg-open-g-report.md",
        },
      ],
      timing: { export_seconds: 0.13 },
    };
    invokeMock.mockResolvedValueOnce(result);

    const returned = await requestExport({ body_width: 60.0 }, "/Users/example/exports");

    expect(returned).toEqual(result);
    expect(invokeMock).toHaveBeenCalledWith("engine_export", {
      parameters: { schema: PARAMETERS_SCHEMA, values: { body_width: 60.0 } },
      output_directory: "/Users/example/exports",
    });
  });

  it("propagates a rejected invoke() call (structured EngineError) unchanged", async () => {
    const engineError = { code: "export_permission_denied", message: "denied" };
    invokeMock.mockRejectedValueOnce(engineError);

    await expect(requestExport({}, "/readonly")).rejects.toEqual(engineError);
  });
});
