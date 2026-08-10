import { beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import { createParameterPanelController } from "./parameter_panel";
import { PARAMETERS_SCHEMA, type ZeroRodParametersValues } from "./parameters";

// Real returned-shape payload — exactly the canonical defaults documented
// in docs/contracts/ZEROROD-PARAMETERS-V1.md, in the same envelope shape
// engine_parameters_defaults actually returns (§41 of the M2 mandate: a
// pure frontend integration/state test using a real returned payload,
// mocked only at the Tauri invoke() boundary — the same boundary M1's own
// tests already mock).
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

function scalarInput(container: HTMLElement, field: string): HTMLInputElement {
  const el = container.querySelector<HTMLInputElement>(`[data-field="${field}"] input`);
  if (!el) throw new Error(`no input for field ${field}`);
  return el;
}

function scalarError(container: HTMLElement, field: string): string {
  return container.querySelector(`[data-field="${field}"] .parameter-error`)?.textContent ?? "";
}

function setValue(input: HTMLInputElement, value: string): void {
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

function preloadDefaults(): void {
  invokeMock.mockResolvedValueOnce({ schema: PARAMETERS_SCHEMA, values: DEFAULT_VALUES });
}

let container: HTMLDivElement;

beforeEach(() => {
  invokeMock.mockReset();
  container = document.createElement("div");
  document.body.appendChild(container);
});

describe("loading and error states", () => {
  it("shows a loading state while defaults are in flight", async () => {
    let resolvePromise!: (value: unknown) => void;
    invokeMock.mockReturnValueOnce(new Promise((resolve) => (resolvePromise = resolve)));

    const panel = createParameterPanelController(container);
    const loadPromise = panel.load();
    expect(container.querySelector('[data-state="loading"]')).toBeTruthy();

    resolvePromise({ schema: PARAMETERS_SCHEMA, values: DEFAULT_VALUES });
    await loadPromise;
    expect(container.querySelector('[data-state="loading"]')).toBeFalsy();
  });

  it("shows a structured error state when defaults fail to load, without crashing", async () => {
    invokeMock.mockRejectedValueOnce({ code: "internal_error", message: "sidecar unavailable" });
    const panel = createParameterPanelController(container);
    await panel.load();

    const errorEl = container.querySelector('[data-state="error"]');
    expect(errorEl).toBeTruthy();
    expect(errorEl?.textContent).toContain("internal_error");
    expect(container.querySelector(".parameter-panel")).toBeFalsy();
  });
});

describe("field coverage and defaults population", () => {
  it("renders all 16 user-editable fields, populated from canonical defaults", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    // 16 contract fields total: project_name (text) + 14 numeric + 1 gauge-array field.
    const scalarFieldCount = container.querySelectorAll(".parameter-field:not(.parameter-field--gauges)").length;
    expect(scalarFieldCount).toBe(15);
    expect(container.querySelectorAll(".gauge-item")).toHaveLength(3);

    expect(scalarInput(container, "body_width").value).toBe("38");
    expect(scalarInput(container, "project_name").value).toBe("CBG Open G");
  });

  it("shows the correct unit per field (mm, inch, none)", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    expect(container.querySelector('[data-field="body_width"] .parameter-unit')?.textContent).toBe("mm");
    expect(container.querySelector('[data-field="project_name"] .parameter-unit')).toBeFalsy();
    const gaugeUnits = container.querySelectorAll(".gauge-item .parameter-unit");
    expect(gaugeUnits.length).toBe(3);
    gaugeUnits.forEach((el) => expect(el.textContent).toBe("in"));
  });

  it("represents string gauges as one control per entry, in order", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    const gaugeInputs = Array.from(container.querySelectorAll<HTMLInputElement>(".gauge-item input"));
    expect(gaugeInputs.map((el) => el.value)).toEqual(["0.036", "0.026", "0.017"]);
  });
});

describe("editing and dirty state", () => {
  it("updates the local draft and shows a dirty/modified indicator on a numeric edit", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    const badge = container.querySelector(".parameter-dirty-badge")!;
    expect(badge.classList.contains("is-visible")).toBe(false);

    setValue(scalarInput(container, "body_width"), "60");
    expect(badge.classList.contains("is-visible")).toBe(true);
  });

  it("updates the local draft on a project_name edit and marks it dirty", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    setValue(scalarInput(container, "project_name"), "My Rod");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(true);
  });

  it("marks dirty on a gauge edit", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    const gaugeInput = container.querySelector<HTMLInputElement>('[data-gauge-index="0"] input')!;
    setValue(gaugeInput, "0.048");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(true);
  });
});

describe("reset", () => {
  it("restores canonical defaults and clears dirty state", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    setValue(scalarInput(container, "body_width"), "99");
    setValue(container.querySelector<HTMLInputElement>('[data-gauge-index="0"] input')!, "0.099");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(true);

    container.querySelector<HTMLButtonElement>('[data-action="reset"]')!.click();

    expect(scalarInput(container, "body_width").value).toBe("38");
    expect(container.querySelector<HTMLInputElement>('[data-gauge-index="0"] input')!.value).toBe("0.036");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(false);
  });
});

describe("local validation feedback", () => {
  it("shows an error for non-numeric input and clears it after correction", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    const input = scalarInput(container, "body_width");
    setValue(input, "abc");
    expect(scalarError(container, "body_width")).toMatch(/finite number/);
    expect(input.getAttribute("aria-invalid")).toBe("true");

    setValue(input, "42.5");
    expect(scalarError(container, "body_width")).toBe("");
    expect(input.getAttribute("aria-invalid")).toBe("false");
  });

  it("rejects NaN", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();
    setValue(scalarInput(container, "body_width"), "NaN");
    expect(scalarError(container, "body_width")).toMatch(/finite number/);
  });

  it("rejects Infinity", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();
    setValue(scalarInput(container, "body_width"), "Infinity");
    expect(scalarError(container, "body_width")).toMatch(/finite number/);
  });

  it("gives contract-range feedback for a documented positive-only field", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();
    setValue(scalarInput(container, "rod_diameter"), "-1");
    expect(scalarError(container, "rod_diameter")).toMatch(/greater than 0/);
  });

  it("disables Apply while any field is invalid, enables it once corrected", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();
    const applyButton = container.querySelector<HTMLButtonElement>('[data-action="apply"]')!;
    expect(applyButton.disabled).toBe(false);

    setValue(scalarInput(container, "body_width"), "abc");
    expect(applyButton.disabled).toBe(true);

    setValue(scalarInput(container, "body_width"), "50");
    expect(applyButton.disabled).toBe(false);
  });
});

describe("Apply", () => {
  it("records the accepted request and shows a not-yet-connected message, without invoking preview", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    setValue(scalarInput(container, "body_width"), "60");
    container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.click();

    const accepted = panel.getAcceptedRequest();
    expect(accepted?.schema).toBe(PARAMETERS_SCHEMA);
    expect(accepted?.values.body_width).toBe(60);

    const message = container.querySelector(".parameter-apply-message");
    expect(message?.textContent).toMatch(/not yet connected/);

    const previewCalls = invokeMock.mock.calls.filter(
      ([command]) => command === "engine_preview_mesh_with_parameters" || command === "engine_preview_mesh",
    );
    expect(previewCalls).toHaveLength(0);
  });
});

describe("draft serialization", () => {
  it("produces a valid zerorod-parameters/v1 shape for a fully valid draft", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    setValue(scalarInput(container, "body_width"), "60");
    container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.click();
    expect(panel.getAcceptedRequest()?.values).toMatchObject({ body_width: 60 });
  });

  it("does not record an accepted request while the draft is invalid", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    setValue(scalarInput(container, "body_width"), "abc");
    // Apply is disabled, but even a defensive click must not fabricate an
    // accepted request from an invalid draft.
    container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.click();
    expect(panel.getAcceptedRequest()).toBeNull();
  });
});

describe("no automatic preview IPC on edit", () => {
  it("never calls a preview-regenerating command while the user edits fields", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    setValue(scalarInput(container, "body_width"), "60");
    setValue(scalarInput(container, "project_name"), "New Name");
    setValue(container.querySelector<HTMLInputElement>('[data-gauge-index="0"] input')!, "0.048");
    container.querySelector<HTMLButtonElement>('[data-action="add-gauge"]')!.click();

    const previewCalls = invokeMock.mock.calls.filter(
      ([command]) => command === "engine_preview_mesh_with_parameters" || command === "engine_preview_mesh",
    );
    expect(previewCalls).toHaveLength(0);
    // Exactly the one initial parameters_defaults call, nothing else.
    expect(invokeMock).toHaveBeenCalledTimes(1);
  });
});

describe("gauge add/remove", () => {
  it("adds a new gauge control that starts invalid (required)", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    container.querySelector<HTMLButtonElement>('[data-action="add-gauge"]')!.click();
    const gaugeItems = container.querySelectorAll(".gauge-item");
    expect(gaugeItems).toHaveLength(4);
    expect(gaugeItems[3].querySelector(".parameter-error")?.textContent).toMatch(/required/);
  });

  it("disables remove when only one gauge remains", async () => {
    preloadDefaults();
    const panel = createParameterPanelController(container);
    await panel.load();

    container.querySelector<HTMLButtonElement>('[data-gauge-index="1"] [data-action="remove-gauge"]')?.click();
    container.querySelector<HTMLButtonElement>('[data-gauge-index="0"] [data-action="remove-gauge"]')?.click();
    expect(container.querySelectorAll(".gauge-item")).toHaveLength(1);
    const removeButton = container.querySelector<HTMLButtonElement>('[data-action="remove-gauge"]')!;
    expect(removeButton.disabled).toBe(true);
  });
});
