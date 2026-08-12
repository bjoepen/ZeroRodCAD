import { beforeEach, describe, expect, it, vi } from "vitest";

const selectProjectOpenFileMock = vi.fn();
const selectProjectSaveFileMock = vi.fn();
const requestProjectOpenMock = vi.fn();
const requestProjectSaveMock = vi.fn();
const fetchDefaultParametersMock = vi.fn();

vi.mock("./project", () => ({
  selectProjectOpenFile: (...args: unknown[]) => selectProjectOpenFileMock(...args),
  selectProjectSaveFile: (...args: unknown[]) => selectProjectSaveFileMock(...args),
  requestProjectOpen: (...args: unknown[]) => requestProjectOpenMock(...args),
  requestProjectSave: (...args: unknown[]) => requestProjectSaveMock(...args),
}));

vi.mock("./parameters", () => ({
  fetchDefaultParameters: (...args: unknown[]) => fetchDefaultParametersMock(...args),
}));

import { createProjectPanelController, type ProjectPanelIO } from "./project_panel";
import type { ZeroRodParametersValues } from "./parameters";
import type { LivePreviewStatus } from "./parameter_panel";

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

const EDITED: ZeroRodParametersValues = { ...DEFAULTS, body_width: 60.0 };

let container: HTMLDivElement;
let accepted: ZeroRodParametersValues | null;
let uncommittedDraft: boolean;
let livePreviewStatus: LivePreviewStatus;
let io: ProjectPanelIO;
let loadProjectValuesMock: ReturnType<typeof vi.fn<ProjectPanelIO["loadProjectValues"]>>;

function newButton(): HTMLButtonElement {
  return container.querySelector<HTMLButtonElement>('[data-action="new"]')!;
}
function openButton(): HTMLButtonElement {
  return container.querySelector<HTMLButtonElement>('[data-action="open"]')!;
}
function saveButton(): HTMLButtonElement {
  return container.querySelector<HTMLButtonElement>('[data-action="save"]')!;
}
function saveAsButton(): HTMLButtonElement {
  return container.querySelector<HTMLButtonElement>('[data-action="save-as"]')!;
}
function guardCancelButton(): HTMLButtonElement | null {
  return container.querySelector<HTMLButtonElement>('[data-action="guard-cancel"]');
}
function guardDiscardButton(): HTMLButtonElement | null {
  return container.querySelector<HTMLButtonElement>('[data-action="guard-discard"]');
}
function guardSaveButton(): HTMLButtonElement | null {
  return container.querySelector<HTMLButtonElement>('[data-action="guard-save"]');
}
function panelState(): string | null {
  return container.querySelector(".project-panel")?.getAttribute("data-state") ?? null;
}
function projectName(): string {
  return container.querySelector(".project-name")?.textContent ?? "";
}
function isDirtyShown(): boolean {
  return container.querySelector(".project-dirty-indicator") !== null;
}

async function flush(): Promise<void> {
  // Some flows chain several real async calls (e.g. the guard's Save path
  // into the deferred action's own dialog + IPC round trip) — enough ticks
  // for the longest chain (Save-As dialog -> save -> settle -> Open dialog
  // -> open -> loadProjectValues) to fully settle.
  for (let i = 0; i < 8; i++) {
    await Promise.resolve();
  }
}

beforeEach(() => {
  selectProjectOpenFileMock.mockReset();
  selectProjectSaveFileMock.mockReset();
  requestProjectOpenMock.mockReset();
  requestProjectSaveMock.mockReset();
  fetchDefaultParametersMock.mockReset();
  fetchDefaultParametersMock.mockResolvedValue(DEFAULTS);

  container = document.createElement("div");
  document.body.appendChild(container);

  accepted = DEFAULTS;
  uncommittedDraft = false;
  livePreviewStatus = "up-to-date";
  loadProjectValuesMock = vi.fn().mockResolvedValue({ ok: true });
  io = {
    getAccepted: () => accepted,
    hasUncommittedDraft: () => uncommittedDraft,
    getLivePreviewStatus: () => livePreviewStatus,
    loadProjectValues: (values) => loadProjectValuesMock(values),
  };
});

describe("initial rendering", () => {
  it("renders New/Open/Save/Save As controls, starting as an untitled, non-dirty project", () => {
    createProjectPanelController(container, io);
    expect(newButton()).toBeTruthy();
    expect(openButton()).toBeTruthy();
    expect(saveButton()).toBeTruthy();
    expect(saveAsButton()).toBeTruthy();
    expect(projectName()).toBe("Untitled project");
    expect(isDirtyShown()).toBe(false);
  });

  it("disables Save/Save As when nothing has been accepted yet", () => {
    accepted = null;
    createProjectPanelController(container, io);
    expect(saveButton().disabled).toBe(true);
    expect(saveAsButton().disabled).toBe(true);
  });

  it("disables Save/Save As while live preview is pending or updating (§23)", () => {
    livePreviewStatus = "pending";
    createProjectPanelController(container, io);
    expect(saveButton().disabled).toBe(true);
    expect(saveAsButton().disabled).toBe(true);
  });

  it("enables Save/Save As when live preview last settled with an error (§23, mirrors export)", () => {
    livePreviewStatus = "error";
    createProjectPanelController(container, io);
    expect(saveButton().disabled).toBe(false);
  });
});

describe("New — no unsaved changes", () => {
  it("creates a new project from canonical defaults, driving a real preview", async () => {
    createProjectPanelController(container, io);
    newButton().click();
    await flush();

    expect(fetchDefaultParametersMock).toHaveBeenCalled();
    expect(loadProjectValuesMock).toHaveBeenCalledWith(DEFAULTS);
    expect(panelState()).toBe("idle");
    expect(projectName()).toBe("Untitled project");
    expect(isDirtyShown()).toBe(false);
  });
});

describe("Open — no unsaved changes", () => {
  it("opens a chosen file and loads its values through the real preview pipeline", async () => {
    selectProjectOpenFileMock.mockResolvedValueOnce("/tmp/projects/alt.zerorod");
    requestProjectOpenMock.mockResolvedValueOnce({ values: EDITED });

    createProjectPanelController(container, io);
    openButton().click();
    await flush();

    expect(requestProjectOpenMock).toHaveBeenCalledWith("/tmp/projects/alt.zerorod");
    expect(loadProjectValuesMock).toHaveBeenCalledWith(EDITED);
    expect(projectName()).toBe("alt.zerorod");
    expect(panelState()).toBe("idle");
  });

  it("does nothing when the native dialog is cancelled", async () => {
    selectProjectOpenFileMock.mockResolvedValueOnce(null);
    createProjectPanelController(container, io);
    openButton().click();
    await flush();

    expect(requestProjectOpenMock).not.toHaveBeenCalled();
    expect(loadProjectValuesMock).not.toHaveBeenCalled();
    expect(panelState()).toBe("idle");
    expect(projectName()).toBe("Untitled project");
  });

  it("leaves the current project/session untouched on a failed open (§12 atomicity)", async () => {
    selectProjectOpenFileMock.mockResolvedValueOnce("/tmp/projects/broken.zerorod");
    requestProjectOpenMock.mockRejectedValueOnce({ code: "project_invalid", message: "bad" });

    createProjectPanelController(container, io);
    openButton().click();
    await flush();

    expect(loadProjectValuesMock).not.toHaveBeenCalled();
    expect(projectName()).toBe("Untitled project");
    expect(panelState()).toBe("error");
    expect(container.querySelector(".project-error")?.textContent).toContain(
      "not a valid ZeroRodCAD project",
    );
  });
});

describe("Save", () => {
  it("Save with no current path behaves like Save As", async () => {
    selectProjectSaveFileMock.mockResolvedValueOnce("/tmp/projects/cbg-open-g.zerorod");
    requestProjectSaveMock.mockResolvedValueOnce({ path: "/tmp/projects/cbg-open-g.zerorod" });

    createProjectPanelController(container, io);
    saveButton().click();
    await flush();

    expect(selectProjectSaveFileMock).toHaveBeenCalledWith("CBG Open G.zerorod");
    expect(requestProjectSaveMock).toHaveBeenCalledWith(DEFAULTS, "/tmp/projects/cbg-open-g.zerorod");
    expect(projectName()).toBe("cbg-open-g.zerorod");
    expect(panelState()).toBe("idle");
  });

  it("Save with an existing current path writes directly, no dialog", async () => {
    // Establish a current path first via a successful Save As.
    selectProjectSaveFileMock.mockResolvedValueOnce("/tmp/projects/cbg-open-g.zerorod");
    requestProjectSaveMock.mockResolvedValueOnce({ path: "/tmp/projects/cbg-open-g.zerorod" });
    createProjectPanelController(container, io);
    saveAsButton().click();
    await flush();
    selectProjectSaveFileMock.mockClear();

    accepted = EDITED;
    requestProjectSaveMock.mockResolvedValueOnce({ path: "/tmp/projects/cbg-open-g.zerorod" });
    saveButton().click();
    await flush();

    expect(selectProjectSaveFileMock).not.toHaveBeenCalled();
    expect(requestProjectSaveMock).toHaveBeenCalledWith(EDITED, "/tmp/projects/cbg-open-g.zerorod");
  });

  it("a cancelled Save As dialog leaves everything unchanged", async () => {
    selectProjectSaveFileMock.mockResolvedValueOnce(null);
    createProjectPanelController(container, io);
    saveAsButton().click();
    await flush();

    expect(requestProjectSaveMock).not.toHaveBeenCalled();
    expect(projectName()).toBe("Untitled project");
    expect(panelState()).toBe("idle");
  });

  it("a failed Save surfaces a structured error and does not clear the dirty state", async () => {
    accepted = EDITED;
    selectProjectSaveFileMock.mockResolvedValueOnce("/tmp/projects/cbg-open-g.zerorod");
    requestProjectSaveMock.mockRejectedValueOnce({
      code: "project_permission_denied",
      message: "denied",
    });

    createProjectPanelController(container, io);
    saveAsButton().click();
    await flush();

    expect(panelState()).toBe("error");
    expect(container.querySelector(".project-error")?.textContent).toContain("Permission denied");
    // No baseline was recorded — this project is still "Untitled" (dirty
    // indicator computation is exercised in project_state.test.ts directly).
    expect(projectName()).toBe("Untitled project");
  });
});

describe("Unsaved-changes guard — New/Open (§17/§21 of the M1 mandate)", () => {
  beforeEach(() => {
    uncommittedDraft = true; // simplest way to force `shouldGuardAgainstDataLoss` true
  });

  it("shows the Save/Discard/Cancel dialog instead of immediately creating a new project", async () => {
    createProjectPanelController(container, io);
    newButton().click();
    await flush();

    expect(panelState()).toBe("confirm_unsaved");
    expect(loadProjectValuesMock).not.toHaveBeenCalled();
    expect(guardSaveButton()).toBeTruthy();
    expect(guardDiscardButton()).toBeTruthy();
    expect(guardCancelButton()).toBeTruthy();
  });

  it("Cancel aborts New entirely — nothing changes", async () => {
    createProjectPanelController(container, io);
    newButton().click();
    await flush();
    guardCancelButton()!.click();
    await flush();

    expect(panelState()).toBe("idle");
    expect(loadProjectValuesMock).not.toHaveBeenCalled();
    expect(fetchDefaultParametersMock).not.toHaveBeenCalled();
  });

  it("Discard proceeds with New, losing the unsaved changes", async () => {
    createProjectPanelController(container, io);
    newButton().click();
    await flush();
    guardDiscardButton()!.click();
    await flush();

    expect(loadProjectValuesMock).toHaveBeenCalledWith(DEFAULTS);
    expect(panelState()).toBe("idle");
  });

  it("Save (with no current path yet) opens Save As, then proceeds with the original Open action", async () => {
    selectProjectOpenFileMock.mockResolvedValueOnce("/tmp/projects/alt.zerorod");
    requestProjectOpenMock.mockResolvedValueOnce({ values: EDITED });
    selectProjectSaveFileMock.mockResolvedValueOnce("/tmp/projects/cbg-open-g.zerorod");
    requestProjectSaveMock.mockResolvedValueOnce({ path: "/tmp/projects/cbg-open-g.zerorod" });

    createProjectPanelController(container, io);
    openButton().click();
    await flush();
    expect(panelState()).toBe("confirm_unsaved");

    guardSaveButton()!.click();
    await flush();

    expect(requestProjectSaveMock).toHaveBeenCalledWith(DEFAULTS, "/tmp/projects/cbg-open-g.zerorod");
    expect(requestProjectOpenMock).toHaveBeenCalledWith("/tmp/projects/alt.zerorod");
    expect(loadProjectValuesMock).toHaveBeenCalledWith(EDITED);
    expect(panelState()).toBe("idle");
  });

  it("§18: cancelling the Save-As sub-dialog cancels the ORIGINAL action, not just the sub-dialog", async () => {
    selectProjectSaveFileMock.mockResolvedValueOnce(null);

    createProjectPanelController(container, io);
    newButton().click();
    await flush();
    guardSaveButton()!.click();
    await flush();

    expect(requestProjectSaveMock).not.toHaveBeenCalled();
    expect(fetchDefaultParametersMock).not.toHaveBeenCalled();
    expect(panelState()).toBe("idle");
  });

  it("a failed Save inside the guard keeps the dialog open with an inline error, and does not proceed", async () => {
    selectProjectSaveFileMock.mockResolvedValueOnce("/tmp/projects/cbg-open-g.zerorod");
    requestProjectSaveMock.mockRejectedValueOnce({ code: "project_write_failed", message: "disk full" });

    createProjectPanelController(container, io);
    newButton().click();
    await flush();
    guardSaveButton()!.click();
    await flush();

    expect(panelState()).toBe("confirm_unsaved");
    expect(container.querySelector(".project-error")?.textContent).toContain("could not be saved");
    expect(loadProjectValuesMock).not.toHaveBeenCalled();
  });
});

describe("confirmQuit (§19/§20 of the M1 mandate)", () => {
  it("resolves true immediately when there is nothing unsaved", async () => {
    const panel = createProjectPanelController(container, io);
    await expect(panel.confirmQuit()).resolves.toBe(true);
  });

  it("shows the guard and resolves false on Cancel", async () => {
    uncommittedDraft = true;
    const panel = createProjectPanelController(container, io);
    const promise = panel.confirmQuit();
    await flush();
    expect(panelState()).toBe("confirm_unsaved");

    guardCancelButton()!.click();
    await expect(promise).resolves.toBe(false);
  });

  it("resolves true on Discard, without saving anything", async () => {
    uncommittedDraft = true;
    const panel = createProjectPanelController(container, io);
    const promise = panel.confirmQuit();
    await flush();

    guardDiscardButton()!.click();
    await expect(promise).resolves.toBe(true);
    expect(requestProjectSaveMock).not.toHaveBeenCalled();
  });

  it("resolves true on a successful Save", async () => {
    uncommittedDraft = true;
    selectProjectSaveFileMock.mockResolvedValueOnce("/tmp/projects/cbg-open-g.zerorod");
    requestProjectSaveMock.mockResolvedValueOnce({ path: "/tmp/projects/cbg-open-g.zerorod" });

    const panel = createProjectPanelController(container, io);
    const promise = panel.confirmQuit();
    await flush();

    guardSaveButton()!.click();
    await expect(promise).resolves.toBe(true);
  });

  it("does not resolve while a Save attempt fails — the caller keeps waiting, window stays open", async () => {
    uncommittedDraft = true;
    selectProjectSaveFileMock.mockResolvedValueOnce("/tmp/projects/cbg-open-g.zerorod");
    requestProjectSaveMock.mockRejectedValueOnce({ code: "project_write_failed", message: "disk full" });

    const panel = createProjectPanelController(container, io);
    const promise = panel.confirmQuit();
    await flush();
    guardSaveButton()!.click();
    await flush();

    expect(panelState()).toBe("confirm_unsaved");
    // Resolve it now via Cancel so the test itself doesn't hang.
    guardCancelButton()!.click();
    await expect(promise).resolves.toBe(false);
  });
});
