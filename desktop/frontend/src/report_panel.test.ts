import { beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import { createReportPanelController, type ReportPanelIO } from "./report_panel";
import type { ZeroRodParametersValues } from "./parameters";

const DEFAULT_VALUES: ZeroRodParametersValues = {
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

const ALTERNATE_VALUES: ZeroRodParametersValues = { ...DEFAULT_VALUES, body_width: 60.0 };

let container: HTMLDivElement;
let getAccepted: ReturnType<typeof vi.fn<ReportPanelIO["getAccepted"]>>;
let io: ReportPanelIO;

async function flush(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

function toggleButton(): HTMLButtonElement {
  return container.querySelector<HTMLButtonElement>('[data-action="report-toggle"]')!;
}

beforeEach(() => {
  invokeMock.mockReset();
  container = document.createElement("div");
  document.body.appendChild(container);
  getAccepted = vi.fn().mockReturnValue(DEFAULT_VALUES);
  io = { getAccepted };
});

describe("createReportPanelController", () => {
  it("does not fetch before the user opens it (§21)", () => {
    createReportPanelController(container, io);
    expect(invokeMock).not.toHaveBeenCalled();
    expect(container.querySelector(".report-panel")).toBeFalsy();
  });

  it("fetches for the accepted state on open and renders it", async () => {
    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report – CBG Open G" });
    createReportPanelController(container, io);

    toggleButton().click();
    await flush();

    expect(invokeMock).toHaveBeenCalledWith("engine_report", {
      parameters: { schema: "zerorod-parameters/v1", values: DEFAULT_VALUES },
    });
    expect(container.querySelector(".report-content")?.innerHTML).toContain(
      "Instrument Report – CBG Open G",
    );
  });

  it("never sources the draft — only io.getAccepted() (§18)", async () => {
    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report" });
    createReportPanelController(container, io);
    toggleButton().click();
    await flush();

    expect(getAccepted).toHaveBeenCalled();
  });

  it("shows a friendly error, not a crash, when the request fails, and offers Retry (§22)", async () => {
    invokeMock.mockRejectedValueOnce({ code: "geometry_error", message: "boom" });
    createReportPanelController(container, io);

    toggleButton().click();
    await flush();

    expect(container.querySelector('[role="alert"]')).toBeTruthy();
    expect(container.textContent).toContain("geometry_error: boom");
    expect(container.querySelector('[data-action="report-retry"]')).toBeTruthy();
  });

  it("Retry re-fetches and can succeed after a prior failure", async () => {
    invokeMock.mockRejectedValueOnce({ code: "timeout", message: "sidecar did not respond" });
    createReportPanelController(container, io);
    toggleButton().click();
    await flush();

    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report" });
    container.querySelector<HTMLButtonElement>('[data-action="report-retry"]')!.click();
    await flush();

    expect(container.querySelector(".report-content")).toBeTruthy();
    expect(container.querySelector('[role="alert"]')).toBeFalsy();
  });

  it("shows a friendly local error (not a crash) when there is no accepted model yet", async () => {
    getAccepted.mockReturnValue(null);
    createReportPanelController(container, io);
    toggleButton().click();
    await flush();

    expect(container.textContent).toContain("No accepted model yet.");
    expect(invokeMock).not.toHaveBeenCalled();
  });

  it("collapses on a second click without an extra fetch", async () => {
    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report" });
    createReportPanelController(container, io);
    toggleButton().click();
    await flush();

    toggleButton().click();
    expect(container.querySelector(".report-panel")).toBeFalsy();
    expect(invokeMock).toHaveBeenCalledTimes(1);
  });

  it("refreshIfVisible() is a no-op while closed", () => {
    const controller = createReportPanelController(container, io);
    controller.refreshIfVisible();
    expect(invokeMock).not.toHaveBeenCalled();
  });

  it("refreshIfVisible() re-fetches when open and accepted actually changed", async () => {
    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report – 38mm" });
    const controller = createReportPanelController(container, io);
    toggleButton().click();
    await flush();
    expect(invokeMock).toHaveBeenCalledTimes(1);

    getAccepted.mockReturnValue(ALTERNATE_VALUES);
    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report – 60mm" });
    controller.refreshIfVisible();
    await flush();

    expect(invokeMock).toHaveBeenCalledTimes(2);
    expect(container.querySelector(".report-content")?.innerHTML).toContain("60mm");
  });

  it("refreshIfVisible() does NOT re-fetch when accepted is unchanged (avoids duplicate requests on every keystroke, §21)", async () => {
    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report" });
    const controller = createReportPanelController(container, io);
    toggleButton().click();
    await flush();
    expect(invokeMock).toHaveBeenCalledTimes(1);

    // Same values, e.g. a live-preview status transition unrelated to a
    // real accepted-state change (pending/updating churn).
    controller.refreshIfVisible();
    controller.refreshIfVisible();
    await flush();

    expect(invokeMock).toHaveBeenCalledTimes(1);
  });

  it("dispose() does not throw", () => {
    const controller = createReportPanelController(container, io);
    expect(() => controller.dispose()).not.toThrow();
  });
});
