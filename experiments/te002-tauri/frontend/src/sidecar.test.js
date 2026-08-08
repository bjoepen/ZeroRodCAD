import { describe, expect, it, vi, beforeEach } from "vitest";

const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args) => invokeMock(...args),
}));

const { requestPreview, SidecarTimeoutError, SidecarProcessError } = await import("./sidecar.js");

beforeEach(() => {
  invokeMock.mockReset();
});

describe("requestPreview", () => {
  it("calls the request_preview command and returns the result", async () => {
    const meshResult = { schema: "zerorod-mesh/v1", meshes: [] };
    invokeMock.mockResolvedValue(meshResult);
    const result = await requestPreview();
    expect(invokeMock).toHaveBeenCalledWith("request_preview");
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

  it("handles an error object without code/message gracefully", async () => {
    invokeMock.mockRejectedValue("plain string failure");
    await expect(requestPreview()).rejects.toBeInstanceOf(SidecarProcessError);
  });
});
