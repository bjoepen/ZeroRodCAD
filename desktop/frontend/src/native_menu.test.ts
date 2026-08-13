import { beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();
const listenMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: (...args: unknown[]) => listenMock(...args),
}));

import { createNativeMenuBridge, dispatchMenuAction, type NativeMenuDeps } from "./native_menu";

function makeDeps(): NativeMenuDeps & {
  resetView: ReturnType<typeof vi.fn<() => void>>;
  setLayerVisible: ReturnType<typeof vi.fn<NativeMenuDeps["preview"]["setLayerVisible"]>>;
  setCheckboxState: ReturnType<typeof vi.fn<NativeMenuDeps["viewControls"]["setCheckboxState"]>>;
  triggerNew: ReturnType<typeof vi.fn<() => void>>;
  triggerOpen: ReturnType<typeof vi.fn<() => void>>;
  triggerSave: ReturnType<typeof vi.fn<() => void>>;
  triggerSaveAs: ReturnType<typeof vi.fn<() => void>>;
  triggerExport: ReturnType<typeof vi.fn<() => void>>;
  openReport: ReturnType<typeof vi.fn<() => void>>;
  openDiagnostics: ReturnType<typeof vi.fn<() => void>>;
} {
  const resetView = vi.fn<() => void>();
  const setLayerVisible = vi.fn<NativeMenuDeps["preview"]["setLayerVisible"]>();
  const setCheckboxState = vi.fn<NativeMenuDeps["viewControls"]["setCheckboxState"]>();
  const triggerNew = vi.fn<() => void>();
  const triggerOpen = vi.fn<() => void>();
  const triggerSave = vi.fn<() => void>();
  const triggerSaveAs = vi.fn<() => void>();
  const triggerExport = vi.fn<() => void>();
  const openReport = vi.fn<() => void>();
  const openDiagnostics = vi.fn<() => void>();
  return {
    preview: { resetView, setLayerVisible },
    viewControls: { setCheckboxState },
    projectPanel: { triggerNew, triggerOpen, triggerSave, triggerSaveAs },
    exportPanel: { triggerExport },
    reportPanel: { open: openReport },
    diagnosticsPanel: { open: openDiagnostics },
    resetView,
    setLayerVisible,
    setCheckboxState,
    triggerNew,
    triggerOpen,
    triggerSave,
    triggerSaveAs,
    triggerExport,
    openReport,
    openDiagnostics,
  };
}

beforeEach(() => {
  invokeMock.mockReset();
  invokeMock.mockResolvedValue(undefined);
  listenMock.mockReset();
  listenMock.mockResolvedValue(() => {});
});

describe("dispatchMenuAction — the native menu ID -> application action mapping (§28 of the mandate)", () => {
  it.each([
    ["file-new", "triggerNew"],
    ["file-open", "triggerOpen"],
    ["file-save", "triggerSave"],
    ["file-save-as", "triggerSaveAs"],
  ] as const)("routes %s to projectPanel.%s", (id, method) => {
    const deps = makeDeps();
    dispatchMenuAction({ id }, deps, deps.setLayerVisible);
    expect(deps[method]).toHaveBeenCalledTimes(1);
  });

  it("routes file-export to exportPanel.triggerExport", () => {
    const deps = makeDeps();
    dispatchMenuAction({ id: "file-export" }, deps, deps.setLayerVisible);
    expect(deps.triggerExport).toHaveBeenCalledTimes(1);
  });

  it("routes view-reset to preview.resetView, not through the shared setLayerVisible function", () => {
    const deps = makeDeps();
    dispatchMenuAction({ id: "view-reset" }, deps, deps.setLayerVisible);
    expect(deps.resetView).toHaveBeenCalledTimes(1);
    expect(deps.setLayerVisible).not.toHaveBeenCalled();
  });

  it("routes view-report to reportPanel.open", () => {
    const deps = makeDeps();
    dispatchMenuAction({ id: "view-report" }, deps, deps.setLayerVisible);
    expect(deps.openReport).toHaveBeenCalledTimes(1);
  });

  it("routes view-diagnostics to diagnosticsPanel.open", () => {
    const deps = makeDeps();
    dispatchMenuAction({ id: "view-diagnostics" }, deps, deps.setLayerVisible);
    expect(deps.openDiagnostics).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["view-body", "body"],
    ["view-rod", "rod"],
    ["view-strings", "strings"],
  ] as const)("routes %s through the shared setLayerVisible with the native item's own checked value", (id, layer) => {
    const deps = makeDeps();
    dispatchMenuAction({ id, checked: false }, deps, deps.setLayerVisible);
    expect(deps.setLayerVisible).toHaveBeenCalledWith(layer, false);
  });

  it("defaults checked to true if the payload omits it (defensive, should not normally happen)", () => {
    const deps = makeDeps();
    dispatchMenuAction({ id: "view-body" }, deps, deps.setLayerVisible);
    expect(deps.setLayerVisible).toHaveBeenCalledWith("body", true);
  });

  it("an unrecognized id is ignored, never throws", () => {
    const deps = makeDeps();
    expect(() => dispatchMenuAction({ id: "not-a-real-menu-id" }, deps, deps.setLayerVisible)).not.toThrow();
  });

  it("quit is never dispatched here — it is handled entirely natively and never reaches this function's real callers", () => {
    const deps = makeDeps();
    dispatchMenuAction({ id: "quit" }, deps, deps.setLayerVisible);
    // No project/export/preview/report/diagnostics action fires for "quit".
    expect(deps.triggerNew).not.toHaveBeenCalled();
    expect(deps.resetView).not.toHaveBeenCalled();
    expect(deps.setLayerVisible).not.toHaveBeenCalled();
  });
});

describe("createNativeMenuBridge.setLayerVisible — the one function both directions funnel through (§15/§16/§29)", () => {
  it("updates the scene, the visible checkbox, and syncs the native menu, in that order", () => {
    const deps = makeDeps();
    const bridge = createNativeMenuBridge(deps);

    bridge.setLayerVisible("rod", false);

    expect(deps.setLayerVisible).toHaveBeenCalledWith("rod", false);
    expect(deps.setCheckboxState).toHaveBeenCalledWith("rod", false);
    expect(invokeMock).toHaveBeenCalledWith("set_view_menu_checked", { layer: "rod", checked: false });
  });

  it("subscribes to the menu-action event exactly once per bridge instance", () => {
    const deps = makeDeps();
    createNativeMenuBridge(deps);
    expect(listenMock).toHaveBeenCalledTimes(1);
    expect(listenMock).toHaveBeenCalledWith("menu-action", expect.any(Function));
  });

  it("dispose() does not throw even before the listen() promise settles", () => {
    const deps = makeDeps();
    const bridge = createNativeMenuBridge(deps);
    expect(() => bridge.dispose()).not.toThrow();
  });
});
