import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import {
  createParameterPanelController,
  LIVE_PREVIEW_DEBOUNCE_MS,
  type PreviewIO,
} from "./parameter_panel";
import { PARAMETERS_SCHEMA, type ZeroRodParametersValues } from "./parameters";
import type { FetchPreviewResult, ParsedPreviewData } from "./preview";

// Real returned-shape payload — canonical defaults from
// docs/contracts/ZEROROD-PARAMETERS-V1.md, mocked only at the Tauri
// invoke() boundary (same pattern M1/M2/M3 already established).
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

const FAKE_DATA: ParsedPreviewData = {
  meshes: [],
  lines: [],
  bounds: { min: [0, 0, 0], max: [1, 1, 1] },
  roundTripMs: 1,
  geometryParseMs: 1,
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

function liveStatusEl(container: HTMLElement): HTMLElement {
  return container.querySelector<HTMLElement>(".parameter-live-status")!;
}

function preloadDefaults(): void {
  invokeMock.mockResolvedValueOnce({ schema: PARAMETERS_SCHEMA, values: DEFAULT_VALUES });
}

/** Flushes the debounce timer and any immediately-following microtasks —
 * enough for a single-step (schedule → dispatch → settle) sequence under
 * vitest fake timers. */
async function flushDebounceAndSettle(extraMs = 0): Promise<void> {
  await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS + extraMs);
  await Promise.resolve();
  await Promise.resolve();
}

let container: HTMLDivElement;
let fetchPreview: ReturnType<typeof vi.fn<PreviewIO["fetchPreview"]>>;
let commitPreview: ReturnType<typeof vi.fn<PreviewIO["commitPreview"]>>;
let previewIO: PreviewIO;

beforeEach(() => {
  invokeMock.mockReset();
  fetchPreview = vi.fn();
  commitPreview = vi.fn();
  previewIO = { fetchPreview, commitPreview };
  container = document.createElement("div");
  document.body.appendChild(container);
});

async function loadPanel() {
  preloadDefaults();
  const panel = createParameterPanelController(container, previewIO);
  await panel.load();
  return panel;
}

describe("loading and error states", () => {
  it("shows a loading state while defaults are in flight", async () => {
    let resolvePromise!: (value: unknown) => void;
    invokeMock.mockReturnValueOnce(new Promise((resolve) => (resolvePromise = resolve)));

    const panel = createParameterPanelController(container, previewIO);
    const loadPromise = panel.load();
    expect(container.querySelector('[data-state="loading"]')).toBeTruthy();

    resolvePromise({ schema: PARAMETERS_SCHEMA, values: DEFAULT_VALUES });
    await loadPromise;
    expect(container.querySelector('[data-state="loading"]')).toBeFalsy();
  });

  it("shows a structured error state when defaults fail to load, without crashing", async () => {
    invokeMock.mockRejectedValueOnce({ code: "internal_error", message: "sidecar unavailable" });
    const panel = createParameterPanelController(container, previewIO);
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
});

describe("initial state", () => {
  it("accepted equals canonical defaults and live status starts up to date", async () => {
    const panel = await loadPanel();
    expect(panel.getAccepted()).toEqual(DEFAULT_VALUES);
    expect(panel.getAcceptedRequest()?.values).toEqual(DEFAULT_VALUES);
    expect(panel.getLivePreviewStatus()).toBe("up-to-date");
    expect(liveStatusEl(container).dataset.status).toBe("up-to-date");
    expect(fetchPreview).not.toHaveBeenCalled();
    expect(commitPreview).not.toHaveBeenCalled();
  });
});

describe("onChange notification (Build 024 M2 — export panel enablement hook)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("calls onChange once defaults load and settle to up-to-date", async () => {
    const onChange = vi.fn();
    preloadDefaults();
    const panel = createParameterPanelController(container, previewIO, onChange);
    await panel.load();

    expect(onChange).toHaveBeenCalled();
  });

  it("calls onChange synchronously when a live-preview request starts (before it settles)", async () => {
    let resolveFetch!: (value: FetchPreviewResult) => void;
    fetchPreview.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );
    const onChange = vi.fn();
    preloadDefaults();
    const panel = createParameterPanelController(container, previewIO, onChange);
    await panel.load();
    onChange.mockClear();

    setValue(scalarInput(container, "body_width"), "60");
    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS);
    await Promise.resolve();

    expect(panel.getLivePreviewStatus()).toBe("updating");
    expect(onChange).toHaveBeenCalled();

    resolveFetch({ ok: true, data: FAKE_DATA });
    await flushDebounceAndSettle();
  });
});

describe("live preview scheduling — geometry vs. metadata vs. invalid", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("schedules a debounced live preview for a valid geometry edit", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    expect(fetchPreview).not.toHaveBeenCalled();
    expect(panel.getLivePreviewStatus()).toBe("pending");

    await flushDebounceAndSettle();
    expect(fetchPreview).toHaveBeenCalledTimes(1);
    expect(fetchPreview).toHaveBeenCalledWith(expect.objectContaining({ body_width: 60 }));
    expect(commitPreview).toHaveBeenCalledWith(FAKE_DATA);
    expect(panel.getAccepted()?.body_width).toBe(60);
    expect(panel.getLivePreviewStatus()).toBe("up-to-date");
  });

  it("does not schedule anything for a project_name-only edit", async () => {
    const panel = await loadPanel();
    setValue(scalarInput(container, "project_name"), "New Name");
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled();
    expect(panel.getLivePreviewStatus()).toBe("up-to-date");
  });

  it("schedules nothing while the draft is locally invalid", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "abc");
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled();
  });

  it("resumes scheduling once an invalid field is corrected", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "abc");
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled();

    setValue(scalarInput(container, "body_width"), "60");
    await flushDebounceAndSettle();
    expect(fetchPreview).toHaveBeenCalledTimes(1);
  });

  it("cancels a pending geometry request if the draft becomes invalid (any field) before it fires", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "60"); // valid, schedules
    await vi.advanceTimersByTimeAsync(100);
    setValue(scalarInput(container, "rod_diameter"), "abc"); // invalidates the whole draft
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled();
  });

  it("collapses a rapid sequence of edits into a single request for the final value (§11/§23)", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    const panel = await loadPanel();

    for (const width of [4, 45, 6, 60]) {
      setValue(scalarInput(container, "body_width"), String(width));
      await vi.advanceTimersByTimeAsync(50);
    }
    await flushDebounceAndSettle();

    expect(fetchPreview).toHaveBeenCalledTimes(1);
    expect(fetchPreview).toHaveBeenCalledWith(expect.objectContaining({ body_width: 60 }));
    expect(panel.getAccepted()?.body_width).toBe(60);
  });

  it("resets the debounce timer on continued editing", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "40");
    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS - 50);
    setValue(scalarInput(container, "body_width"), "45");
    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS - 50);
    expect(fetchPreview).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchPreview).toHaveBeenCalledTimes(1);
    expect(fetchPreview).toHaveBeenCalledWith(expect.objectContaining({ body_width: 45 }));
  });

  it("issues zero requests when the edit returns to the accepted value before the debounce fires (§36)", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "40");
    await vi.advanceTimersByTimeAsync(100);
    setValue(scalarInput(container, "body_width"), "38"); // back to accepted default
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled();
  });

  it("issues exactly one request when going default -> 40 -> back to default after 40 was already previewed (§36)", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "40");
    await flushDebounceAndSettle();
    expect(fetchPreview).toHaveBeenCalledTimes(1);
    expect(panel.getAccepted()?.body_width).toBe(40);

    setValue(scalarInput(container, "body_width"), "38");
    await flushDebounceAndSettle();
    expect(fetchPreview).toHaveBeenCalledTimes(2);
    expect(fetchPreview).toHaveBeenLastCalledWith(expect.objectContaining({ body_width: 38 }));
  });

  it("follows the same debounce for gauge edits, preserving order", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    await loadPanel();

    setValue(container.querySelector<HTMLInputElement>('[data-gauge-index="1"] input')!, "0.048");
    await flushDebounceAndSettle();

    expect(fetchPreview).toHaveBeenCalledWith(
      expect.objectContaining({ string_gauges_inch: [0.036, 0.048, 0.017] }),
    );
  });

  it("schedules nothing for an invalid temporary gauge state, resumes once corrected", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    await loadPanel();

    const gaugeInput = container.querySelector<HTMLInputElement>('[data-gauge-index="0"] input')!;
    setValue(gaugeInput, "bad");
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled();

    setValue(gaugeInput, "0.040");
    await flushDebounceAndSettle();
    expect(fetchPreview).toHaveBeenCalledTimes(1);
  });
});

describe("error handling and recovery", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("a domain error preserves the old preview (commitPreview never called) and shows the error", async () => {
    fetchPreview.mockResolvedValueOnce({
      ok: false,
      error: { code: "invalid_parameters_domain", message: "bad", details: { errors: ["Groove too big."] } },
    } satisfies FetchPreviewResult);
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    await flushDebounceAndSettle();

    expect(commitPreview).not.toHaveBeenCalled();
    expect(panel.getAccepted()?.body_width).toBe(38); // unchanged
    expect(panel.getLivePreviewStatus()).toBe("error");
    expect(liveStatusEl(container).textContent).toContain("Groove too big.");
  });

  it("recovers automatically once the value is corrected after an error", async () => {
    fetchPreview
      .mockResolvedValueOnce({ ok: false, error: { code: "geometry_error", message: "boom" } })
      .mockResolvedValueOnce({ ok: true, data: FAKE_DATA });
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "999");
    await flushDebounceAndSettle();
    expect(panel.getLivePreviewStatus()).toBe("error");

    setValue(scalarInput(container, "body_width"), "60");
    await flushDebounceAndSettle();
    expect(panel.getLivePreviewStatus()).toBe("up-to-date");
    expect(panel.getAccepted()?.body_width).toBe(60);
    expect(commitPreview).toHaveBeenCalledTimes(1);
  });

  it("associates a field-level error message when the engine error carries details.field", async () => {
    fetchPreview.mockResolvedValueOnce({
      ok: false,
      error: { code: "invalid_parameter_type", message: "must be a number", details: { field: "body_width" } },
    } satisfies FetchPreviewResult);
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    await flushDebounceAndSettle();

    expect(scalarError(container, "body_width")).toBe("must be a number");
  });

  it("error sequence: valid 38 -> invalid domain request -> valid 60 (§39)", async () => {
    fetchPreview
      .mockResolvedValueOnce({ ok: false, error: { code: "invalid_parameters_domain", message: "bad" } })
      .mockResolvedValueOnce({ ok: true, data: FAKE_DATA });
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "999");
    await flushDebounceAndSettle();
    expect(commitPreview).not.toHaveBeenCalled(); // 38 remains visible (never committed anything else)
    expect(panel.getLivePreviewStatus()).toBe("error");

    setValue(scalarInput(container, "body_width"), "60");
    await flushDebounceAndSettle();
    expect(commitPreview).toHaveBeenCalledTimes(1);
    expect(panel.getAccepted()?.body_width).toBe(60);
    expect(panel.getLivePreviewStatus()).toBe("up-to-date");
  });
});

describe("Reset — schedules a debounced default preview, does not dispatch immediately (§19)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("Reset does not itself call fetchPreview", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "60");
    clickReset(container);
    expect(fetchPreview).not.toHaveBeenCalled();
  });

  it("Reset after a live-previewed non-default value schedules (via normal debounce) a request back to defaults", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    await flushDebounceAndSettle();
    expect(panel.getAccepted()?.body_width).toBe(60);

    clickReset(container);
    expect(scalarInput(container, "body_width").value).toBe("38");
    expect(fetchPreview).toHaveBeenCalledTimes(1); // not yet a second call
    await flushDebounceAndSettle();
    expect(fetchPreview).toHaveBeenCalledTimes(2);
    expect(fetchPreview).toHaveBeenLastCalledWith(expect.objectContaining({ body_width: 38 }));
    expect(panel.getAccepted()?.body_width).toBe(38);
  });

  it("Reset issues no request at all if accepted already equals defaults", async () => {
    await loadPanel();
    clickReset(container);
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled();
  });

  it("Reset after only a metadata (project_name) accept does not trigger an unnecessary geometry rebuild", async () => {
    const panel = await loadPanel();
    setValue(scalarInput(container, "project_name"), "My Rod");
    clickApply(container); // metadata-only accept, no engine call
    expect(panel.getAccepted()?.project_name).toBe("My Rod");
    expect(fetchPreview).not.toHaveBeenCalled();

    clickReset(container);
    await flushDebounceAndSettle();
    expect(fetchPreview).not.toHaveBeenCalled(); // geometry was already at defaults throughout
  });
});

describe("Apply — shares the live-preview pipeline (§16/§22)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("Apply flushes a pending debounce immediately instead of waiting", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await Promise.resolve();
    await Promise.resolve();

    expect(fetchPreview).toHaveBeenCalledTimes(1);
    expect(panel.getAccepted()?.body_width).toBe(60);
  });

  it("Apply during a pending debounce does not duplicate the request once the debounce would have fired", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container);
    await Promise.resolve();
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS + 10);

    expect(fetchPreview).toHaveBeenCalledTimes(1);
  });

  it("Apply while a live-preview request is already in flight coalesces deterministically (no parallel requests)", async () => {
    let resolveFirst!: (r: FetchPreviewResult) => void;
    fetchPreview
      .mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValue({ ok: true, data: FAKE_DATA });
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "45");
    await flushDebounceAndSettle(); // now in flight (unresolved)
    expect(fetchPreview).toHaveBeenCalledTimes(1);

    setValue(scalarInput(container, "body_width"), "60");
    clickApply(container); // queued behind the in-flight request
    await Promise.resolve();
    expect(fetchPreview).toHaveBeenCalledTimes(1); // still just the one in flight

    resolveFirst({ ok: true, data: FAKE_DATA });
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    expect(fetchPreview).toHaveBeenCalledTimes(2);
    expect(fetchPreview).toHaveBeenLastCalledWith(expect.objectContaining({ body_width: 60 }));
    expect(panel.getAccepted()?.body_width).toBe(60);
  });

  it("is disabled when there is nothing to apply", async () => {
    await loadPanel();
    expect(container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.disabled).toBe(true);
  });

  it("is disabled while the draft is invalid", async () => {
    await loadPanel();
    setValue(scalarInput(container, "body_width"), "abc");
    expect(container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.disabled).toBe(true);
  });

  it("stays enabled after a live-preview error, allowing an explicit retry", async () => {
    fetchPreview.mockResolvedValueOnce({ ok: false, error: { code: "geometry_error", message: "boom" } });
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "999");
    await flushDebounceAndSettle();
    expect(container.querySelector<HTMLButtonElement>('[data-action="apply"]')!.disabled).toBe(false);
  });

  it("accepts a metadata-only change locally via Apply, without calling fetchPreview", async () => {
    const panel = await loadPanel();
    setValue(scalarInput(container, "project_name"), "My Rod");
    clickApply(container);

    expect(fetchPreview).not.toHaveBeenCalled();
    expect(panel.getAccepted()?.project_name).toBe("My Rod");
    expect(panel.getLivePreviewStatus()).toBe("up-to-date");
  });
});

describe("status transitions and the delayed 'Updating…' indicator (§27/§28)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("moves through pending -> updating -> up-to-date for a successful edit", async () => {
    let resolveFetch!: (r: FetchPreviewResult) => void;
    fetchPreview.mockImplementationOnce(() => new Promise((resolve) => (resolveFetch = resolve)));
    const panel = await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    expect(panel.getLivePreviewStatus()).toBe("pending");

    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS);
    expect(panel.getLivePreviewStatus()).toBe("updating");

    resolveFetch({ ok: true, data: FAKE_DATA });
    await Promise.resolve();
    await Promise.resolve();
    expect(panel.getLivePreviewStatus()).toBe("up-to-date");
  });

  it("does not show 'Updating preview…' text for a fast-resolving request (avoids flicker)", async () => {
    fetchPreview.mockResolvedValueOnce({ ok: true, data: FAKE_DATA });
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS);
    // Request settles on the same microtask turn — well under the display delay.
    await Promise.resolve();
    await Promise.resolve();
    expect(liveStatusEl(container).textContent).not.toContain("Updating preview");
  });

  it("shows 'Updating preview…' text once a request runs past the display delay", async () => {
    let resolveFetch!: (r: FetchPreviewResult) => void;
    fetchPreview.mockImplementationOnce(() => new Promise((resolve) => (resolveFetch = resolve)));
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS); // request starts
    expect(liveStatusEl(container).textContent).not.toContain("Updating preview");
    await vi.advanceTimersByTimeAsync(200); // past the display delay, still unresolved
    expect(liveStatusEl(container).textContent).toContain("Updating preview…");

    resolveFetch({ ok: true, data: FAKE_DATA });
    await Promise.resolve();
    await Promise.resolve();
  });

  it("data-status is always instantly correct even while the display text is delayed", async () => {
    let resolveFetch!: (r: FetchPreviewResult) => void;
    fetchPreview.mockImplementationOnce(() => new Promise((resolve) => (resolveFetch = resolve)));
    await loadPanel();

    setValue(scalarInput(container, "body_width"), "60");
    await vi.advanceTimersByTimeAsync(LIVE_PREVIEW_DEBOUNCE_MS);
    expect(liveStatusEl(container).dataset.status).toBe("updating");

    resolveFetch({ ok: true, data: FAKE_DATA });
    await Promise.resolve();
    await Promise.resolve();
  });
});

describe("repeated update stability (§32)", () => {
  it("handles 100 sequential successful Apply cycles without error or state corruption", async () => {
    fetchPreview.mockResolvedValue({ ok: true, data: FAKE_DATA } satisfies FetchPreviewResult);
    const panel = await loadPanel();

    for (let i = 0; i < 100; i++) {
      const width = 38 + (i % 20);
      setValue(scalarInput(container, "body_width"), String(width));
      clickApply(container);
      // eslint-disable-next-line no-await-in-loop
      await Promise.resolve();
      // eslint-disable-next-line no-await-in-loop
      await Promise.resolve();
    }

    expect(commitPreview).toHaveBeenCalledTimes(fetchPreview.mock.calls.length);
    expect(panel.getLivePreviewStatus()).not.toBe("error");
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

describe("Enter key does not trigger extra requests", () => {
  it("Enter in a numeric field does not submit or dispatch anything", async () => {
    await loadPanel();
    const input = scalarInput(container, "body_width");
    setValue(input, "60");
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(fetchPreview).not.toHaveBeenCalled();
  });
});

// --- Build 025 M1: hasUncommittedDraft / loadProjectValues ---------------

describe("hasUncommittedDraft (§22 of the M1 mandate)", () => {
  it("is false immediately after load", async () => {
    const panel = await loadPanel();
    expect(panel.hasUncommittedDraft()).toBe(false);
  });

  it("is true the moment a field is edited, before the debounce fires", async () => {
    const panel = await loadPanel();
    setValue(scalarInput(container, "body_width"), "60");
    expect(panel.hasUncommittedDraft()).toBe(true);
  });

  it("is true for an INVALID in-progress edit too, not just a valid one", async () => {
    const panel = await loadPanel();
    setValue(scalarInput(container, "body_width"), "not-a-number");
    expect(panel.hasUncommittedDraft()).toBe(true);
    expect(fetchPreview).not.toHaveBeenCalled();
  });

  it("returns to false once the draft is edited back to the accepted value", async () => {
    const panel = await loadPanel();
    setValue(scalarInput(container, "body_width"), "60");
    expect(panel.hasUncommittedDraft()).toBe(true);
    setValue(scalarInput(container, "body_width"), String(DEFAULT_VALUES.body_width));
    expect(panel.hasUncommittedDraft()).toBe(false);
  });

  it("is true again after a successful Apply followed by a further edit", async () => {
    vi.useFakeTimers();
    try {
      const panel = await loadPanel();
      fetchPreview.mockResolvedValueOnce({ ok: true, data: FAKE_DATA });
      setValue(scalarInput(container, "body_width"), "60");
      clickApply(container);
      await vi.advanceTimersByTimeAsync(0);
      await Promise.resolve();
      await Promise.resolve();
      expect(panel.hasUncommittedDraft()).toBe(false);

      setValue(scalarInput(container, "body_depth"), "11");
      expect(panel.hasUncommittedDraft()).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("loadProjectValues (§10/§13 of the M1 mandate)", () => {
  const ALTERNATE_VALUES: ZeroRodParametersValues = {
    ...DEFAULT_VALUES,
    project_name: "Alternate Project",
    body_width: 60.0,
  };

  it("rebuilds the form/accepted state from the given values and renders a real preview", async () => {
    const panel = await loadPanel();
    fetchPreview.mockResolvedValueOnce({ ok: true, data: FAKE_DATA });

    const result = await panel.loadProjectValues(ALTERNATE_VALUES);

    expect(result.ok).toBe(true);
    expect(fetchPreview).toHaveBeenCalledWith(ALTERNATE_VALUES);
    expect(commitPreview).toHaveBeenCalledWith(FAKE_DATA);
    expect(panel.getAccepted()).toEqual(ALTERNATE_VALUES);
    expect(scalarInput(container, "body_width").value).toBe("60");
    expect(panel.hasUncommittedDraft()).toBe(false);
  });

  it("does NOT change the Reset-to-Defaults target — Reset still restores canonical defaults, not the loaded project", async () => {
    const panel = await loadPanel();
    fetchPreview.mockResolvedValueOnce({ ok: true, data: FAKE_DATA });
    await panel.loadProjectValues(ALTERNATE_VALUES);

    clickReset(container);
    expect(scalarInput(container, "body_width").value).toBe(String(DEFAULT_VALUES.body_width));
    expect(scalarInput(container, "project_name").value).toBe(DEFAULT_VALUES.project_name);
  });

  it("surfaces a preview/geometry failure as a structured error without throwing", async () => {
    const panel = await loadPanel();
    fetchPreview.mockResolvedValueOnce({
      ok: false,
      error: { code: "geometry_error", message: "boom" },
    });

    const result = await panel.loadProjectValues(ALTERNATE_VALUES);

    expect(result.ok).toBe(false);
    // The project's parameter values are still committed (§ "New project
    // created, but the preview could not be rendered" — a Level-4 geometry
    // failure is not the same class of problem as a project-file validation
    // failure, and does not roll back the already-validated parameter set).
    expect(panel.getAccepted()).toEqual(ALTERNATE_VALUES);
    expect(commitPreview).not.toHaveBeenCalled();
  });
});
