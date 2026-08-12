import { describe, expect, it, vi, beforeEach } from "vitest";

const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args) => invokeMock(...args),
}));

const {
  requestPreview,
  requestPreviewOneShot,
  shutdownPersistentEngine,
  SidecarTimeoutError,
  SidecarProcessError,
} = await import("./sidecar.js");

beforeEach(() => {
  invokeMock.mockReset();
});

describe("requestPreview (TE-002.1 default: persistent engine)", () => {
  it("calls the persistent_preview command and returns the result", async () => {
    const meshResult = { schema: "zerorod-mesh/v1", meshes: [] };
    invokeMock.mockResolvedValue(meshResult);
    const result = await requestPreview();
    expect(invokeMock).toHaveBeenCalledWith("persistent_preview");
    expect(result).toBe(meshResult);
  });

  it("wraps a timeout error as SidecarTimeoutError", async () => {
    invokeMock.mockRejectedValue({ code: "timeout", message: "sidecar did not respond within 30s" });
    await expect(requestPreview()).rejects.toBeInstanceOf(SidecarTimeoutError);
  });

  it("wraps a process error as SidecarProcessError", async () => {
    invokeMock.mockRejectedValue({ code: "nonzero_exit", message: "sidecar exited with code 1" });
    await expect(requestPreview()).rejects.toBeInstanceOf(SidecarProcessError);
  });

  it("wraps a crash error as SidecarProcessError", async () => {
    invokeMock.mockRejectedValue({ code: "sidecar_crashed", message: "terminated unexpectedly" });
    await expect(requestPreview()).rejects.toBeInstanceOf(SidecarProcessError);
  });

  it("handles an error object without code/message gracefully", async () => {
    invokeMock.mockRejectedValue("plain string failure");
    await expect(requestPreview()).rejects.toBeInstanceOf(SidecarProcessError);
  });
});

describe("requestPreviewOneShot (TE-002 original, kept as reference/fallback)", () => {
  it("calls the request_preview command", async () => {
    const meshResult = { schema: "zerorod-mesh/v1", meshes: [] };
    invokeMock.mockResolvedValue(meshResult);
    const result = await requestPreviewOneShot();
    expect(invokeMock).toHaveBeenCalledWith("request_preview");
    expect(result).toBe(meshResult);
  });

  it("wraps errors the same way as the persistent path", async () => {
    invokeMock.mockRejectedValue({ code: "timeout", message: "x" });
    await expect(requestPreviewOneShot()).rejects.toBeInstanceOf(SidecarTimeoutError);
  });
});

describe("shutdownPersistentEngine", () => {
  it("calls the persistent_shutdown command", async () => {
    invokeMock.mockResolvedValue(undefined);
    await shutdownPersistentEngine();
    expect(invokeMock).toHaveBeenCalledWith("persistent_shutdown");
  });

  it("wraps errors consistently", async () => {
    invokeMock.mockRejectedValue({ code: "internal_error", message: "x" });
    await expect(shutdownPersistentEngine()).rejects.toBeInstanceOf(SidecarProcessError);
  });
});
