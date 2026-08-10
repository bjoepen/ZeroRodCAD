import { beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import { createParameterPanelController, type ApplyParametersFn } from "./parameter_panel";
import { PARAMETERS_SCHEMA, type ZeroRodParametersValues } from "./parameters";

// Real returned-shape payload — canonical defaults from
// docs/contracts/ZEROROD-PARAMETERS-V1.md, mocked only at the Tauri
// invoke() boundary (same pattern M1/M2 already established).
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

function clickApply(container: HTMLElement): void {
  container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.click();
}

function clickReset(container: HTMLElement): void {
  container.querySelector<HTMLButtonElement>('[data-action="reset"]')!.click();
}

function preloadDefaults(): void {
  invokeMock.mockResolvedValueOnce({ schema: PARAMETERS_SCHEMA, values: DEFAULT_VALUES });
}

let container: HTMLDivElement;
let applyParametersMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  invokeMock.mockReset();
  applyParametersMock = vi.fn();
  container = document.createElement("div");
  document.body.appendChild(container);
});

async function loadPanel() {
  preloadDefaults();
  const panel = createParameterPanelController(container, applyParametersMock as unknown as ApplyParametersFn);
  await panel.load();
  return panel;
}

async function waitUntilSettled(panel: { getApplyStatus: () => string }): Promise<void> {
  await vi.waitFor(() => {
    if (panel.getApplyStatus() === "applying") throw new Error("still applying");
  });
}

describe("loading and error states", () => {
  it("shows a loading state while defaults are in flight", async () => {
    let resolvePromise!: (value: unknown) => void;
    invokeMock.mockReturnValueOnce(new Promise((resolve) => (resolvePromise = resolve)));

    const panel = createParameterPanelController(container, applyParametersMock as unknown as ApplyParametersFn);
    const loadPromise = panel.load();
    expect(container.querySelector('[data-state="loading"]')).toBeTruthy();

    resolvePromise({ schema: PARAMETERS_SCHEMA, values: DEFAULT_VALUES });
    await loadPromise;
    expect(container.querySelector('[data-state="loading"]')).toBeFalsy();
  });

  it("shows a structured error state when defaults fail to load, without crashing", async () => {
    invokeMock.mockRejectedValueOnce({ code: "internal_error", message: "sidecar unavailable" });
    const panel = createParameterPanelController(container, applyParametersMock as unknown as ApplyParametersFn);
    await panel.load();

    const errorEl = container.querySelector('[data-state="error"]');
    expect(errorEl).toBeTruthy();
    expect(errorEl?.textContent).toContain("internal_error");
    expect(container.querySelector(".parameter-panel")).toBeFalsy();
  });
});

describe("field coverage and defaults population", () => {
  it("renders all 16 user-editable fields, populated from canonical defaults", async () => {
    await loadPanel();
    const scalarFieldCount = container.querySelectorAll(".parameter-field:not(.parameter-field--gauges)").length;
    expect(scalarFieldCount).toBe(15);
    expect(container.querySelectorAll(".gauge-item")).toHaveLength(3);
    expect(scalarInput(container, "body_width").value).toBe("38");
    expect(scalarInput(container, "project_name").value).toBe("CBG Open G");
  });

  it("shows the correct unit per field (mm, inch, none)", async () => {
    await loadPanel();
    expect(container.querySelector('[data-field="body_width"] .parameter-unit')?.textContent).toBe("mm");
    expect(container.querySelector('[data-field="project_name"] .parameter-unit')).toBeFalsy();
    const gaugeUnits = container.querySelectorAll(".gauge-item .parameter-unit");
    expect(gaugeUnits.length).toBe(3);
    gaugeUnits.forEach((el) => expect(el.textContent).toBe("in"));
  });
});

describe("initial state (§28 of the M3 mandate)", () => {
  it("accepted equals canonical defaults, draft matches, dirty is false", async () => {
    const panel = await loadPanel();
    expect(panel.getAccepted()).toEqual(DEFAULT_VALUES);
    expect(panel.getAcceptedRequest()?.values).toEqual(DEFAULT_VALUES);
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(false);
    expect(panel.getApplyStatus()).toBe("idle");
  });
});

describe("editing never triggers a request", () => {
  it("updates the local draft and marks dirty on a numeric edit, without calling applyParameters", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "60");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(true);
    expect(applyParametersMock).not.toHaveBeenCalled();
  });

  it("never calls applyParameters across a full sequence of edits, gauge add, project_name change", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "60");
    setValue(scalarInput(container, "project_name"), "New Name");
    setValue(container.querySelector<HTMLInputElement>('[data-gauge-index="0"] input')!, "0.048");
    container.querySelector<HTMLButtonElement>('[data-action="add-gauge"]')!.click();
    expect(applyParametersMock).not.toHaveBeenCalled();
    expect(invokeMock).toHaveBeenCalledTimes(1); // only the initial defaults fetch
  });
});

describe("local validation feedback", () => {
  it("shows an error for non-numeric input and clears it after correction", async () => {
    await loadPanel();
    const input = scalarInput(container, "body_width");
    setValue(input, "abc");
    expect(scalarError(container, "body_width")).toMatch(/finite number/);
    expect(input.getAttribute("aria-invalid")).toBe("true");
    setValue(input, "42.5");
    expect(scalarError(container, "body_width")).toBe("");
    expect(input.getAttribute("aria-invalid")).toBe("false");
  });

  it("rejects NaN and Infinity", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "NaN");
    expect(scalarError(container, "body_width")).toMatch(/finite number/);
    setValue(scalarInput(container, "body_width"), "Infinity");
    expect(scalarError(container, "body_width")).toMatch(/finite number/);
  });
});

describe("Apply preconditions (§10/§36 of the M3 mandate)", () => {
  it("Apply is disabled when there are no changes yet", async () => {
    await loadPanel();
    expect(container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.disabled).toBe(true);
  });

  it("Apply is disabled while the draft is invalid, and a defensive click sends nothing", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "abc");
    const applyButton = container.querySelector<HTMLButtonElement>('[data-action="apply"]')!;
    expect(applyButton.disabled).toBe(true);
    applyButton.click();
    expect(applyParametersMock).not.toHaveBeenCalled();
  });

  it("Apply becomes enabled once a valid, dirty change exists", async () => {
    await loadPanel();
    const applyButton = container.querySelector<HTMLButtonElement>('[data-action="apply"]')!;
    setValue(scalarInput(container, "body_width"), "abc");
    expect(applyButton.disabled).toBe(true);
    setValue(scalarInput(container, "body_width"), "60");
    expect(applyButton.disabled).toBe(false);
  });
});

describe("Apply — geometry-changing success/failure", () => {
  it("invokes applyParameters exactly once with the correct zerorod-parameters/v1 values, updates accepted, clears dirty", async () => {
    const panel = await loadPanel();
    applyParametersMock.mockResolvedValueOnce({ ok: true });
    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await waitUntilSettled(panel);

    expect(applyParametersMock).toHaveBeenCalledTimes(1);
    expect(applyParametersMock).toHaveBeenCalledWith(expect.objectContaining({ body_width: 60 }));
    expect(panel.getAccepted()?.body_width).toBe(60);
    expect(panel.getApplyStatus()).toBe("applied");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(false);
  });

  it("failed Apply preserves accepted state and keeps dirty true", async () => {
    const panel = await loadPanel();
    applyParametersMock.mockResolvedValueOnce({
      ok: false,
      error: { code: "geometry_error", message: "geometry generation failed" },
    });
    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await waitUntilSettled(panel);

    expect(panel.getAccepted()?.body_width).toBe(38);
    expect(panel.getApplyStatus()).toBe("error");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(true);
    const message = container.querySelector(".parameter-apply-message");
    expect(message?.textContent).toContain("geometry_error");
  });

  it("displays a field-associated error when the engine error carries details.field", async () => {
    const panel = await loadPanel();
    applyParametersMock.mockResolvedValueOnce({
      ok: false,
      error: {
        code: "invalid_parameter_type",
        message: "body_width must be a number",
        details: { field: "body_width" },
      },
    });
    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await waitUntilSettled(panel);

    expect(scalarError(container, "body_width")).toBe("body_width must be a number");
    expect(scalarInput(container, "body_width").getAttribute("aria-invalid")).toBe("true");
  });

  it("displays a form-level error when the engine error has no field", async () => {
    const panel = await loadPanel();
    applyParametersMock.mockResolvedValueOnce({
      ok: false,
      error: {
        code: "invalid_parameters_domain",
        message: "domain rule violated",
        details: { errors: ["Groove diameter must be smaller than rod diameter."] },
      },
    });
    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await waitUntilSettled(panel);

    const message = container.querySelector(".parameter-apply-message");
    expect(message?.textContent).toContain("Groove diameter must be smaller than rod diameter.");
  });

  it("blocks a second Apply while one is already in flight (no parallel requests)", async () => {
    const panel = await loadPanel();
    let resolveApply!: (value: { ok: boolean }) => void;
    applyParametersMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveApply = resolve;
      }),
    );
    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await vi.waitFor(() => expect(panel.getApplyStatus()).toBe("applying"));

    clickApply(container); // rapid re-activation while applying
    expect(applyParametersMock).toHaveBeenCalledTimes(1);

    resolveApply({ ok: true });
    await waitUntilSettled(panel);
    expect(panel.getApplyStatus()).toBe("applied");
  });

  it("Enter key in a numeric field does not trigger Apply", async () => {
    await loadPanel();
    const input = scalarInput(container, "body_width");
    setValue(input, "60");
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(applyParametersMock).not.toHaveBeenCalled();
  });

  it("sends a gauge change correctly, preserving order", async () => {
    const panel = await loadPanel();
    applyParametersMock.mockResolvedValueOnce({ ok: true });
    setValue(container.querySelector<HTMLInputElement>('[data-gauge-index="1"] input')!, "0.048");
    clickApply(container);
    await waitUntilSettled(panel);

    expect(applyParametersMock).toHaveBeenCalledWith(
      expect.objectContaining({ string_gauges_inch: [0.036, 0.048, 0.017] }),
    );
  });

  it("supports repeated sequential Apply calls without stale state", async () => {
    const panel = await loadPanel();
    for (const width of [60, 45, 38]) {
      applyParametersMock.mockResolvedValueOnce({ ok: true });
      setValue(scalarInput(container, "body_width"), String(width));
      clickApply(container);
      await waitUntilSettled(panel);
      expect(panel.getAccepted()?.body_width).toBe(width);
    }
    expect(applyParametersMock).toHaveBeenCalledTimes(3);
  });
});

describe("Apply — project_name-only change (§24 of the M3 mandate)", () => {
  it("accepts a project_name-only change locally, without calling applyParameters", async () => {
    const panel = await loadPanel();
    setValue(scalarInput(container, "project_name"), "My Rod");
    clickApply(container);
    await waitUntilSettled(panel);

    expect(applyParametersMock).not.toHaveBeenCalled();
    expect(panel.getAccepted()?.project_name).toBe("My Rod");
    expect(panel.getApplyStatus()).toBe("applied");
    expect(container.querySelector(".parameter-apply-message")?.textContent).toMatch(/metadata only/);
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(false);
  });
});

describe("Reset semantics under the M3 accepted-state model (§25/§26)", () => {
  it("Reset alone never calls applyParameters", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "60");
    clickReset(container);
    expect(applyParametersMock).not.toHaveBeenCalled();
  });

  it("Reset after a successful non-default Apply restores defaults into the draft but stays dirty (accepted still differs)", async () => {
    const panel = await loadPanel();
    applyParametersMock.mockResolvedValueOnce({ ok: true });
    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await waitUntilSettled(panel);
    expect(panel.getAccepted()?.body_width).toBe(60);

    applyParametersMock.mockClear();
    clickReset(container);

    expect(scalarInput(container, "body_width").value).toBe("38");
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(true);
    expect(applyParametersMock).not.toHaveBeenCalled();
  });

  it("Applying after that reset restores the default geometry and clears dirty", async () => {
    const panel = await loadPanel();
    applyParametersMock.mockResolvedValueOnce({ ok: true });
    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await waitUntilSettled(panel);

    clickReset(container);
    applyParametersMock.mockResolvedValueOnce({ ok: true });
    clickApply(container);
    await waitUntilSettled(panel);

    expect(panel.getAccepted()?.body_width).toBe(38);
    expect(applyParametersMock).toHaveBeenLastCalledWith(expect.objectContaining({ body_width: 38 }));
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(false);
  });

  it("Reset when accepted already equals defaults leaves dirty false", async () => {
    await loadPanel();
    clickReset(container);
    expect(container.querySelector(".parameter-dirty-badge")?.classList.contains("is-visible")).toBe(false);
  });
});

describe("gauge add/remove", () => {
  it("adds a new gauge control that starts invalid (required)", async () => {
    await loadPanel();
    container.querySelector<HTMLButtonElement>('[data-action="add-gauge"]')!.click();
    const gaugeItems = container.querySelectorAll(".gauge-item");
    expect(gaugeItems).toHaveLength(4);
    expect(gaugeItems[3].querySelector(".parameter-error")?.textContent).toMatch(/required/);
  });

  it("disables remove when only one gauge remains", async () => {
    await loadPanel();
    container.querySelector<HTMLButtonElement>('[data-gauge-index="1"] [data-action="remove-gauge"]')?.click();
    container.querySelector<HTMLButtonElement>('[data-gauge-index="0"] [data-action="remove-gauge"]')?.click();
    expect(container.querySelectorAll(".gauge-item")).toHaveLength(1);
    expect(container.querySelector<HTMLButtonElement>('[data-action="remove-gauge"]')!.disabled).toBe(true);
  });
});
