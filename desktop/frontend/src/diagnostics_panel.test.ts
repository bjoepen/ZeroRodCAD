import { beforeEach, describe, expect, it, vi } from "vitest";
import { createDiagnosticsPanelController, type DiagnosticsIO } from "./diagnostics_panel";
import type { AppInfo } from "./app_info";
import type { EngineStatusInfo, SidecarStatus } from "./engine";

const APP_INFO: AppInfo = { name: "ZeroRodCAD Desktop", version: "0.1.0", build: "025", milestone: "M2" };
const ENGINE_STATUS: EngineStatusInfo = { state: "RUNNING", pid: 4242, last_error: null };
const SIDECAR_STATUS: SidecarStatus = {
  status: "ok",
  pid: 4242,
  python_version: "3.13.14",
  cadquery_version: "2.6.0",
  ocp_variant: "cadquery-ocp-novtk",
  vtk_installed: false,
  milestone: "M2",
};

let container: HTMLDivElement;
let fetchAppInfo: ReturnType<typeof vi.fn<DiagnosticsIO["fetchAppInfo"]>>;
let fetchEngineStatus: ReturnType<typeof vi.fn<DiagnosticsIO["fetchEngineStatus"]>>;
let fetchSidecarStatus: ReturnType<typeof vi.fn<DiagnosticsIO["fetchSidecarStatus"]>>;
let io: DiagnosticsIO;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  fetchAppInfo = vi.fn().mockResolvedValue(APP_INFO);
  fetchEngineStatus = vi.fn().mockResolvedValue(ENGINE_STATUS);
  fetchSidecarStatus = vi.fn().mockResolvedValue(SIDECAR_STATUS);
  io = { fetchAppInfo, fetchEngineStatus, fetchSidecarStatus };
});

function toggleButton(): HTMLButtonElement {
  return container.querySelector<HTMLButtonElement>('[data-action="diagnostics-toggle"]')!;
}

async function flush(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

describe("createDiagnosticsPanelController", () => {
  it("renders only a collapsed toggle, no side effects, on construction (§38 of the mandate)", () => {
    createDiagnosticsPanelController(container, io);

    expect(toggleButton()).toBeTruthy();
    expect(container.querySelector(".diagnostics-panel")).toBeFalsy();
    expect(fetchAppInfo).not.toHaveBeenCalled();
    expect(fetchEngineStatus).not.toHaveBeenCalled();
    expect(fetchSidecarStatus).not.toHaveBeenCalled();
  });

  it("fetches and shows status only once the user opens it — never before", async () => {
    createDiagnosticsPanelController(container, io);
    expect(fetchAppInfo).not.toHaveBeenCalled();

    toggleButton().click();
    await flush();

    expect(fetchAppInfo).toHaveBeenCalledTimes(1);
    expect(fetchEngineStatus).toHaveBeenCalledTimes(1);
    expect(fetchSidecarStatus).toHaveBeenCalledTimes(1);

    const panel = container.querySelector(".diagnostics-panel");
    expect(panel).toBeTruthy();
    expect(panel?.textContent).toContain("ZeroRodCAD Desktop 0.1.0 — Build 025 M2");
    expect(panel?.textContent).toContain("pid 4242");
    expect(panel?.textContent).toContain("3.13.14");
    expect(panel?.textContent).toContain("2.6.0");
    expect(panel?.textContent).toContain("cadquery-ocp-novtk");
    expect(panel?.textContent).toContain("zerorod-parameters/v1");
    expect(panel?.textContent).toContain("zerorod-mesh/v1");
  });

  it("surfaces the last engine error, sanitized, when present", async () => {
    fetchEngineStatus.mockResolvedValue({
      state: "ERROR",
      pid: null,
      last_error: { code: "sidecar_crashed", message: "sidecar terminated unexpectedly" },
    });
    createDiagnosticsPanelController(container, io);
    toggleButton().click();
    await flush();

    expect(container.textContent).toContain("sidecar_crashed: sidecar terminated unexpectedly");
  });

  it("does not fail the whole panel when only the sidecar-specific status is unreachable", async () => {
    fetchSidecarStatus.mockRejectedValue({ code: "timeout", message: "sidecar did not respond" });
    createDiagnosticsPanelController(container, io);
    toggleButton().click();
    await flush();

    // engine_status's own state already covers this — the panel should
    // still render app/engine rows, not collapse into a full error state.
    expect(container.querySelector('[role="alert"]')).toBeFalsy();
    expect(container.textContent).toContain("ZeroRodCAD Desktop 0.1.0");
  });

  it("shows a structured error state if app_info/engine_status themselves fail", async () => {
    fetchAppInfo.mockRejectedValue({ code: "internal_error", message: "bridge unavailable" });
    createDiagnosticsPanelController(container, io);
    toggleButton().click();
    await flush();

    expect(container.querySelector('[role="alert"]')).toBeTruthy();
    expect(container.textContent).toContain("internal_error: bridge unavailable");
  });

  it("collapses again on a second click without re-fetching", async () => {
    createDiagnosticsPanelController(container, io);
    toggleButton().click();
    await flush();
    expect(container.querySelector(".diagnostics-panel")).toBeTruthy();

    toggleButton().click();
    expect(container.querySelector(".diagnostics-panel")).toBeFalsy();
    expect(fetchAppInfo).toHaveBeenCalledTimes(1);
  });

  it("Refresh Status re-fetches without any preview/project/export side effect (§38)", async () => {
    createDiagnosticsPanelController(container, io);
    toggleButton().click();
    await flush();
    fetchAppInfo.mockClear();
    fetchEngineStatus.mockClear();
    fetchSidecarStatus.mockClear();

    container.querySelector<HTMLButtonElement>('[data-action="diagnostics-refresh"]')!.click();
    await flush();

    expect(fetchAppInfo).toHaveBeenCalledTimes(1);
    expect(fetchEngineStatus).toHaveBeenCalledTimes(1);
    expect(fetchSidecarStatus).toHaveBeenCalledTimes(1);
  });

  it("exposes no kill-sidecar / raw-IPC / process-control action (§17 of the mandate)", async () => {
    createDiagnosticsPanelController(container, io);
    toggleButton().click();
    await flush();

    const buttons = Array.from(container.querySelectorAll("button")).map((b) => b.textContent);
    expect(buttons).toEqual(["Hide Diagnostics", "Refresh Status"]);
  });

  it("dispose() does not throw", () => {
    const controller = createDiagnosticsPanelController(container, io);
    expect(() => controller.dispose()).not.toThrow();
  });
});
