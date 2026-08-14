import { beforeEach, describe, expect, it, vi } from "vitest";

const selectExportDirectoryMock = vi.fn();
const requestExportPreflightMock = vi.fn();
const requestExportMock = vi.fn();

vi.mock("./export", () => ({
  selectExportDirectory: (...args: unknown[]) => selectExportDirectoryMock(...args),
  requestExportPreflight: (...args: unknown[]) => requestExportPreflightMock(...args),
  requestExport: (...args: unknown[]) => requestExportMock(...args),
}));

import { createExportPanelController, type ExportPanelIO } from "./export_panel";
import { PARAMETERS_SCHEMA, type ParametersRequest } from "./parameters";
import type { LivePreviewStatus } from "./parameter_panel";

const ACCEPTED_REQUEST: ParametersRequest = {
  schema: PARAMETERS_SCHEMA,
  values: { project_name: "CBG Open G", body_width: 38.0 },
};

const EXPORT_RESULT = {
  output_directory: "/Users/example/exports",
  files: [
    { role: "body_stl", filename: "cbg-open-g-body.stl", path: "/Users/example/exports/cbg-open-g-body.stl" },
    {
      role: "assembly_step",
      filename: "cbg-open-g-assembly.step",
      path: "/Users/example/exports/cbg-open-g-assembly.step",
    },
    { role: "report_markdown", filename: "cbg-open-g-report.md", path: "/Users/example/exports/cbg-open-g-report.md" },
  ],
  timing: { export_seconds: 0.13 },
};

function noConflictPreflight(directory: string) {
  return {
    output_directory: directory,
    expected_files: [{ role: "body_stl", filename: "cbg-open-g-body.stl" }],
    conflicts: [],
    has_conflicts: false,
  };
}

function conflictPreflight(directory: string) {
  return {
    output_directory: directory,
    expected_files: [{ role: "body_stl", filename: "cbg-open-g-body.stl" }],
    conflicts: [{ role: "body_stl", filename: "cbg-open-g-body.stl" }],
    has_conflicts: true,
  };
}

let container: HTMLDivElement;
let accepted: ParametersRequest | null;
let livePreviewStatus: LivePreviewStatus;
let io: ExportPanelIO;

function triggerButton(): HTMLButtonElement {
  return container.querySelector<HTMLButtonElement>('[data-action="export"]')!;
}

function panelState(): string | null {
  return container.querySelector(".export-panel")?.getAttribute("data-state") ?? null;
}

async function flush(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

beforeEach(() => {
  selectExportDirectoryMock.mockReset();
  requestExportPreflightMock.mockReset();
  requestExportMock.mockReset();
  container = document.createElement("div");
  document.body.appendChild(container);
  accepted = ACCEPTED_REQUEST;
  livePreviewStatus = "up-to-date";
  io = {
    getAcceptedRequest: () => accepted,
    getLivePreviewStatus: () => livePreviewStatus,
  };
});

describe("rendering and enablement", () => {
  it("renders the export control", () => {
    createExportPanelController(container, io);
    expect(triggerButton()).toBeTruthy();
    expect(triggerButton().textContent).toContain("Export Model");
  });

  it("is disabled when no accepted model state is available", () => {
    accepted = null;
    createExportPanelController(container, io);
    expect(triggerButton().disabled).toBe(true);
  });

  it("is enabled for a stable accepted model", () => {
    createExportPanelController(container, io);
    expect(triggerButton().disabled).toBe(false);
  });

  it("is disabled while live preview is pending", () => {
    livePreviewStatus = "pending";
    createExportPanelController(container, io);
    expect(triggerButton().disabled).toBe(true);
  });

  it("is disabled while live preview is updating (in flight)", () => {
    livePreviewStatus = "updating";
    createExportPanelController(container, io);
    expect(triggerButton().disabled).toBe(true);
  });

  it("remains enabled when the last live-preview attempt errored (accepted still valid)", () => {
    livePreviewStatus = "error";
    createExportPanelController(container, io);
    expect(triggerButton().disabled).toBe(false);
  });

  it("refreshEnablement re-renders to reflect a changed accepted/status", () => {
    const controller = createExportPanelController(container, io);
    expect(triggerButton().disabled).toBe(false);

    livePreviewStatus = "updating";
    controller.refreshEnablement();
    expect(triggerButton().disabled).toBe(true);

    livePreviewStatus = "up-to-date";
    controller.refreshEnablement();
    expect(triggerButton().disabled).toBe(false);
  });
});

describe("dialog invocation and cancellation", () => {
  it("invokes the directory dialog exactly once per click", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce(null);
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(selectExportDirectoryMock).toHaveBeenCalledTimes(1);
  });

  it("dialog cancellation produces no preflight/export call and returns to idle without an error", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce(null);
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(requestExportPreflightMock).not.toHaveBeenCalled();
    expect(requestExportMock).not.toHaveBeenCalled();
    expect(panelState()).toBe("idle");
    expect(container.querySelector(".export-error")).toBeFalsy();
    expect(container.querySelector(".export-note")?.textContent).toContain("cancelled");
  });
});

describe("triggerExport (Build 025 M4, native File -> Export Model… menu entry point, §20/§33)", () => {
  it("does exactly what clicking the export button does", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce(null);
    const panel = createExportPanelController(container, io);

    panel.triggerExport();
    await flush();

    expect(selectExportDirectoryMock).toHaveBeenCalledTimes(1);
  });

  it("safely no-ops when export isn't currently enabled (mirrors the disabled button)", async () => {
    accepted = null;
    const panel = createExportPanelController(container, io);

    panel.triggerExport();
    await flush();

    expect(selectExportDirectoryMock).not.toHaveBeenCalled();
  });
});

describe("preflight and export request", () => {
  it("a valid destination triggers preflight, then export when there is no conflict", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/Users/example/exports");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/Users/example/exports"));
    requestExportMock.mockResolvedValueOnce(EXPORT_RESULT);
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(requestExportPreflightMock).toHaveBeenCalledWith(ACCEPTED_REQUEST.values, "/Users/example/exports");
    expect(requestExportMock).toHaveBeenCalledWith(ACCEPTED_REQUEST.values, "/Users/example/exports");
  });

  it("sends exactly the accepted parameter values, not a reconstructed/raw draft", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockResolvedValueOnce(EXPORT_RESULT);
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    const sentValues = requestExportMock.mock.calls[0][0];
    expect(sentValues).toBe(ACCEPTED_REQUEST.values);
  });

  it("does not dispatch a second export while one is in flight (duplicate click blocked)", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    let resolveExport!: (value: typeof EXPORT_RESULT) => void;
    requestExportMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveExport = resolve;
      }),
    );
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();
    expect(panelState()).toBe("exporting");
    expect(triggerButton().disabled).toBe(true);

    // A second click while exporting must not be possible via the trigger —
    // simulate a stray click anyway to prove the handler itself no-ops.
    triggerButton().click();
    await flush();
    expect(requestExportMock).toHaveBeenCalledTimes(1);

    resolveExport(EXPORT_RESULT);
    await flush();
  });
});

describe("success and error presentation", () => {
  it("shows the generated outputs from the backend result, not a frontend-reconstructed filename set", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockResolvedValueOnce(EXPORT_RESULT);
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(panelState()).toBe("success");
    const text = container.querySelector(".export-success")?.textContent ?? "";
    for (const file of EXPORT_RESULT.files) {
      expect(text).toContain(file.filename);
    }
    expect(text).toContain(EXPORT_RESULT.output_directory);
  });

  it("displays a concise structured error message on export failure", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockRejectedValueOnce({ code: "export_permission_denied", message: "denied" });
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(panelState()).toBe("error");
    expect(container.querySelector(".export-error")?.textContent).toContain("Permission denied");
  });

  it("does not show export_incomplete as a success state", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockRejectedValueOnce({
      code: "export_incomplete",
      message: "export reported success but did not produce all expected output files: body_stl",
      details: { missing: ["body_stl"] },
    });
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(panelState()).toBe("error");
    expect(container.querySelector(".export-success")).toBeFalsy();
    expect(container.querySelector(".export-error")?.textContent).toContain("did not complete");
    expect(container.querySelector(".export-error")?.textContent).toContain("body_stl");
  });

  it("surfaces a preflight failure as a structured error, without attempting export", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockRejectedValueOnce({
      code: "invalid_destination",
      message: "output_directory must be a non-empty string",
    });
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(requestExportMock).not.toHaveBeenCalled();
    expect(panelState()).toBe("error");
  });
});

describe("overwrite conflict flow", () => {
  it("detects a conflict and shows a confirmation instead of exporting immediately", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(conflictPreflight("/dest"));
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(panelState()).toBe("confirm_overwrite");
    expect(requestExportMock).not.toHaveBeenCalled();
    expect(container.querySelector(".export-confirm")?.textContent).toContain("cbg-open-g-body.stl");
  });

  it("cancel produces no export and returns to idle with the model unchanged", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(conflictPreflight("/dest"));
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();
    container.querySelector<HTMLButtonElement>('[data-action="cancel-overwrite"]')!.click();
    await flush();

    expect(requestExportMock).not.toHaveBeenCalled();
    expect(panelState()).toBe("idle");
  });

  it("confirm triggers exactly one export call, without a redundant second preflight", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(conflictPreflight("/dest"));
    requestExportMock.mockResolvedValueOnce(EXPORT_RESULT);
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();
    container.querySelector<HTMLButtonElement>('[data-action="confirm-overwrite"]')!.click();
    await flush();

    expect(requestExportPreflightMock).toHaveBeenCalledTimes(1);
    expect(requestExportMock).toHaveBeenCalledTimes(1);
    expect(panelState()).toBe("success");
  });
});

describe("Build 024 M3 — robustness and error recovery", () => {
  it("a malformed/invalid export result (Rust-side validation rejection) never shows success", async () => {
    // Build 024 M3: commands.rs now structurally validates the sidecar's
    // export result before it can ever resolve as a success from invoke()
    // — a malformed shape surfaces as a rejected promise with this code,
    // never as a resolved-but-broken ExportResult object.
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockRejectedValueOnce({
      code: "invalid_export_result",
      message: "'files' is required",
    });
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(panelState()).toBe("error");
    expect(container.querySelector(".export-success")).toBeFalsy();
    expect(container.querySelector(".export-error")?.textContent).toContain("unexpected result");
  });

  it("a stale error clears once a subsequent export succeeds", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockRejectedValueOnce({ code: "export_write_failed", message: "disk error" });
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();
    expect(panelState()).toBe("error");

    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockResolvedValueOnce(EXPORT_RESULT);

    triggerButton().click();
    await flush();

    expect(panelState()).toBe("success");
    expect(container.querySelector(".export-error")).toBeFalsy();
  });

  it("a stale success/error note clears once the user starts a new export attempt", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce(null);
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();
    expect(container.querySelector(".export-note")?.textContent).toContain("cancelled");

    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockResolvedValueOnce(noConflictPreflight("/dest"));
    requestExportMock.mockResolvedValueOnce(EXPORT_RESULT);

    triggerButton().click();
    await flush();

    expect(panelState()).toBe("success");
    expect(container.querySelector(".export-note")).toBeFalsy();
  });

  it("preflight rejecting with invalid_export_result is a structured error, not a crash", async () => {
    selectExportDirectoryMock.mockResolvedValueOnce("/dest");
    requestExportPreflightMock.mockRejectedValueOnce({
      code: "invalid_export_result",
      message: "'has_conflicts' must be a boolean",
    });
    createExportPanelController(container, io);

    triggerButton().click();
    await flush();

    expect(requestExportMock).not.toHaveBeenCalled();
    expect(panelState()).toBe("error");
  });
});
