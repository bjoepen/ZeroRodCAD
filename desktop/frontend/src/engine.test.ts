import { beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import {
  fetchEngineStatus,
  fetchSidecarStatus,
  isEngineError,
  pingEngine,
  requestPreviewSummary,
  shutdownEngine,
} from "./engine";

beforeEach(() => {
  invokeMock.mockReset();
});

describe("isEngineError", () => {
  it("recognizes a well-formed engine error", () => {
    expect(isEngineError({ code: "timeout", message: "no response" })).toBe(true);
  });

  it("rejects plain strings, null, and objects missing fields", () => {
    expect(isEngineError("timeout")).toBe(false);
    expect(isEngineError(null)).toBe(false);
    expect(isEngineError({ code: "timeout" })).toBe(false);
  });
});

describe("fetchEngineStatus", () => {
  it("returns the engine status state reported by Rust", async () => {
    invokeMock.mockResolvedValueOnce({ state: "STOPPED", pid: null, last_error: null });
    const status = await fetchEngineStatus();
    expect(status.state).toBe("STOPPED");
    expect(invokeMock).toHaveBeenCalledWith("engine_status");
  });

  it("propagates a RUNNING state with a pid once the sidecar has started", async () => {
    invokeMock.mockResolvedValueOnce({ state: "RUNNING", pid: 4242, last_error: null });
    const status = await fetchEngineStatus();
    expect(status.state).toBe("RUNNING");
    expect(status.pid).toBe(4242);
  });
});

describe("pingEngine", () => {
  it("resolves with the sidecar's ping result on success", async () => {
    invokeMock.mockResolvedValueOnce({ status: "ok", pid: 123 });
    const result = await pingEngine();
    expect(result).toEqual({ status: "ok", pid: 123 });
    expect(invokeMock).toHaveBeenCalledWith("engine_ping");
  });

  it("propagates a structured EngineError when the sidecar cannot be reached", async () => {
    invokeMock.mockRejectedValueOnce({
      code: "sidecar_missing",
      message: "could not resolve onedir sidecar resource",
    });
    await expect(pingEngine()).rejects.toSatisfy(
      (error: unknown) => isEngineError(error) && error.code === "sidecar_missing",
    );
  });

  it("propagates a timeout error without swallowing it", async () => {
    invokeMock.mockRejectedValueOnce({ code: "timeout", message: "sidecar did not respond" });
    await expect(pingEngine()).rejects.toSatisfy(
      (error: unknown) => isEngineError(error) && error.code === "timeout",
    );
  });
});

describe("fetchSidecarStatus", () => {
  it("resolves with the sidecar's own status payload", async () => {
    invokeMock.mockResolvedValueOnce({
      status: "ready",
      pid: 1,
      python_version: "3.13.14",
      cadquery_version: "2.8.0",
      ocp_variant: "cadquery-ocp-novtk",
      vtk_installed: false,
    });
    const status = await fetchSidecarStatus();
    expect(status.vtk_installed).toBe(false);
    expect(status.ocp_variant).toBe("cadquery-ocp-novtk");
  });
});

describe("requestPreviewSummary", () => {
  it("resolves with a validated mesh summary on success", async () => {
    invokeMock.mockResolvedValueOnce({
      schema: "zerorod-mesh/v1",
      mesh_count: 2,
      total_vertices: 866,
      total_triangles: 850,
      line_count: 1,
      bounds: { min: [-19, -4, 0], max: [19, 14, 8.1] },
    });
    const summary = await requestPreviewSummary();
    expect(summary.schema).toBe("zerorod-mesh/v1");
    expect(summary.mesh_count).toBe(2);
  });

  it("propagates an invalid_mesh EngineError without hiding it as a generic failure", async () => {
    invokeMock.mockRejectedValueOnce({
      code: "invalid_mesh",
      message: "generated mesh failed validation: meshes must be a non-empty list",
    });
    await expect(requestPreviewSummary()).rejects.toSatisfy(
      (error: unknown) => isEngineError(error) && error.code === "invalid_mesh",
    );
  });
});

describe("shutdownEngine", () => {
  it("calls the engine_shutdown command", async () => {
    invokeMock.mockResolvedValueOnce(undefined);
    await shutdownEngine();
    expect(invokeMock).toHaveBeenCalledWith("engine_shutdown");
  });
});
