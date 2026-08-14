import { beforeEach, describe, expect, it, vi } from "vitest";
import { createViewControlsController, type ViewControlsIO } from "./view_controls";

let container: HTMLDivElement;
let resetView: ReturnType<typeof vi.fn<ViewControlsIO["resetView"]>>;
let setLayerVisible: ReturnType<typeof vi.fn<ViewControlsIO["setLayerVisible"]>>;
let isLayerVisible: ReturnType<typeof vi.fn<ViewControlsIO["isLayerVisible"]>>;
let io: ViewControlsIO;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  resetView = vi.fn();
  setLayerVisible = vi.fn();
  isLayerVisible = vi.fn().mockReturnValue(true);
  io = { resetView, setLayerVisible, isLayerVisible };
});

function checkbox(layer: string): HTMLInputElement {
  return container.querySelector<HTMLInputElement>(`#view-layer-${layer}`)!;
}

describe("createViewControlsController", () => {
  it("renders Body/Rod/Strings checkboxes and a Reset View button, all initially checked (§14)", () => {
    createViewControlsController(container, io);

    expect(checkbox("body").checked).toBe(true);
    expect(checkbox("rod").checked).toBe(true);
    expect(checkbox("strings").checked).toBe(true);
    expect(container.querySelector('[data-action="reset-view"]')).toBeTruthy();
  });

  it("reflects the IO's current visibility at construction, not always-checked", () => {
    isLayerVisible.mockImplementation((layer) => layer !== "rod");
    createViewControlsController(container, io);

    expect(checkbox("body").checked).toBe(true);
    expect(checkbox("rod").checked).toBe(false);
    expect(checkbox("strings").checked).toBe(true);
  });

  it("unchecking Body calls setLayerVisible(body, false) and nothing else", () => {
    createViewControlsController(container, io);

    checkbox("body").checked = false;
    checkbox("body").dispatchEvent(new Event("change"));

    expect(setLayerVisible).toHaveBeenCalledTimes(1);
    expect(setLayerVisible).toHaveBeenCalledWith("body", false);
    expect(resetView).not.toHaveBeenCalled();
  });

  it("each checkbox toggles independently", () => {
    createViewControlsController(container, io);

    checkbox("rod").checked = false;
    checkbox("rod").dispatchEvent(new Event("change"));
    checkbox("strings").checked = false;
    checkbox("strings").dispatchEvent(new Event("change"));

    expect(setLayerVisible).toHaveBeenNthCalledWith(1, "rod", false);
    expect(setLayerVisible).toHaveBeenNthCalledWith(2, "strings", false);
    expect(setLayerVisible).toHaveBeenCalledTimes(2);
  });

  it("clicking Reset View calls resetView() and never setLayerVisible", () => {
    createViewControlsController(container, io);

    container.querySelector<HTMLButtonElement>('[data-action="reset-view"]')!.click();

    expect(resetView).toHaveBeenCalledTimes(1);
    expect(setLayerVisible).not.toHaveBeenCalled();
  });

  it("uses plain product labels, not Three.js/internal terminology (§15)", () => {
    createViewControlsController(container, io);
    const text = container.textContent ?? "";
    expect(text).toContain("Body");
    expect(text).toContain("Rod");
    expect(text).toContain("Strings");
    expect(text).toContain("Reset View");
    expect(text.toLowerCase()).not.toContain("group");
    expect(text.toLowerCase()).not.toContain("mesh");
    expect(text.toLowerCase()).not.toContain("three.js");
  });

  it("every checkbox has an explicit, associated label (§15/§55 accessibility)", () => {
    createViewControlsController(container, io);
    for (const layer of ["body", "rod", "strings"]) {
      const input = checkbox(layer);
      const label = container.querySelector(`label[for="${input.id}"]`);
      expect(label).toBeTruthy();
    }
  });

  it("dispose() does not throw", () => {
    const controller = createViewControlsController(container, io);
    expect(() => controller.dispose()).not.toThrow();
  });

  it("setCheckboxState() (Build 025 M4 — reflects a native-menu-driven change, §15/§29) updates the visible checkbox without calling setLayerVisible again", () => {
    const controller = createViewControlsController(container, io);

    controller.setCheckboxState("body", false);

    expect(checkbox("body").checked).toBe(false);
    expect(setLayerVisible).not.toHaveBeenCalled();
  });

  it("setCheckboxState() does not fire the checkbox's own change handler (no feedback loop)", () => {
    const controller = createViewControlsController(container, io);
    controller.setCheckboxState("rod", false);
    controller.setCheckboxState("rod", true);

    expect(setLayerVisible).not.toHaveBeenCalled();
  });
});
