import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createStartupController,
  friendlyStartupMessage,
  startupErrorDetail,
  type StartupIO,
} from "./startup";
import type { ParameterPanelLoadResult } from "./parameter_panel";

let container: HTMLDivElement;

beforeEach(() => {
  vi.useFakeTimers();
  container = document.createElement("div");
  document.body.appendChild(container);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("friendlyStartupMessage (pure)", () => {
  it("uses an engine-could-not-start message for a defaults-stage failure", () => {
    expect(
      friendlyStartupMessage({ ok: false, stage: "defaults", error: { code: "x", message: "y" } }),
    ).toBe("ZeroRodCAD's engine could not start.");
  });

  it("uses an initial-model message for a preview-stage failure", () => {
    expect(
      friendlyStartupMessage({ ok: false, stage: "preview", error: { code: "x", message: "y" } }),
    ).toBe("ZeroRodCAD could not load the initial model.");
  });
});

describe("startupErrorDetail (pure)", () => {
  it("formats a structured EngineError as code: message", () => {
    expect(startupErrorDetail({ code: "timeout", message: "sidecar did not respond" })).toBe(
      "timeout: sidecar did not respond",
    );
  });

  it("never throws on an unstructured error, falling back to String()", () => {
    expect(startupErrorDetail("boom")).toBe("boom");
    expect(startupErrorDetail(null)).toBe("null");
  });

  it("never surfaces a raw traceback shape beyond code/message even if present", () => {
    const detail = startupErrorDetail({
      code: "internal_error",
      message: "sidecar unavailable",
      details: { traceback: "Traceback (most recent call last): ..." },
    });
    expect(detail).toBe("internal_error: sidecar unavailable");
    expect(detail).not.toContain("Traceback");
  });
});

function makeIO(run: () => Promise<ParameterPanelLoadResult>): StartupIO {
  return { run };
}

describe("createStartupController", () => {
  it("renders nothing on a successful startup — no persistent 'ready' banner (§21)", async () => {
    const io = makeIO(async () => ({ ok: true }));
    const controller = createStartupController(container, io);

    const startPromise = controller.start();
    await vi.runAllTimersAsync();
    await startPromise;

    expect(container.innerHTML).toBe("");
  });

  it("does not show 'Preparing…' for a fast-resolving startup (avoids flicker, §20/§48)", async () => {
    const io = makeIO(async () => ({ ok: true }));
    const controller = createStartupController(container, io);

    // Resolves on the same microtask turn, well under the display delay —
    // no fake-timer advance at all before awaiting.
    await controller.start();

    expect(container.textContent).not.toContain("Preparing");
  });

  it("shows 'Preparing ZeroRodCAD…' once startup runs past the display delay", async () => {
    let resolveRun!: (result: ParameterPanelLoadResult) => void;
    const io = makeIO(() => new Promise((resolve) => (resolveRun = resolve)));
    const controller = createStartupController(container, io);

    const startPromise = controller.start();
    await vi.advanceTimersByTimeAsync(300);
    expect(container.textContent).toContain("Preparing ZeroRodCAD…");

    resolveRun({ ok: true });
    await startPromise;
    expect(container.innerHTML).toBe("");
  });

  it("shows a friendly message with Retry/Show Details on failure, never a raw code in the headline", async () => {
    const io = makeIO(async () => ({
      ok: false,
      stage: "defaults",
      error: { code: "internal_error", message: "sidecar unavailable" },
    }));
    const controller = createStartupController(container, io);

    const startPromise = controller.start();
    await vi.runAllTimersAsync();
    await startPromise;

    const alertEl = container.querySelector('[role="alert"]');
    expect(alertEl).toBeTruthy();
    expect(alertEl?.querySelector("p")?.textContent).toBe("ZeroRodCAD's engine could not start.");
    // The sanitized code/message IS in the DOM (Show Details reveals it —
    // covered below) but must not be part of the default-visible headline.
    expect(container.querySelector<HTMLElement>(".startup-error-detail")?.hidden).toBe(true);
    expect(container.querySelector('[data-action="startup-retry"]')).toBeTruthy();
    expect(container.querySelector('[data-action="startup-details"]')).toBeTruthy();
  });

  it("Show Details reveals the sanitized technical detail, toggled by the same button", async () => {
    const io = makeIO(async () => ({
      ok: false,
      stage: "preview",
      error: { code: "timeout", message: "sidecar did not respond" },
    }));
    const controller = createStartupController(container, io);
    await controller.start();

    const detailsButton = container.querySelector<HTMLButtonElement>('[data-action="startup-details"]')!;
    const detailEl = container.querySelector<HTMLElement>(".startup-error-detail")!;
    expect(detailEl.hidden).toBe(true);

    detailsButton.click();
    expect(detailEl.hidden).toBe(false);
    expect(detailEl.textContent).toBe("timeout: sidecar did not respond");
    expect(detailsButton.getAttribute("aria-expanded")).toBe("true");

    detailsButton.click();
    expect(detailEl.hidden).toBe(true);
    expect(detailsButton.getAttribute("aria-expanded")).toBe("false");
  });

  it("Retry re-runs io.run() and clears the failure surface on success (§25)", async () => {
    const run = vi
      .fn<StartupIO["run"]>()
      .mockResolvedValueOnce({ ok: false, stage: "defaults", error: { code: "x", message: "y" } })
      .mockResolvedValueOnce({ ok: true });
    const controller = createStartupController(container, makeIO(run));
    await controller.start();

    expect(run).toHaveBeenCalledTimes(1);
    container.querySelector<HTMLButtonElement>('[data-action="startup-retry"]')!.click();
    await vi.runAllTimersAsync();

    expect(run).toHaveBeenCalledTimes(2);
    expect(container.innerHTML).toBe("");
  });

  it("Retry after a second failure shows the new failure, not a stale one", async () => {
    const run = vi
      .fn<StartupIO["run"]>()
      .mockResolvedValueOnce({ ok: false, stage: "defaults", error: { code: "first", message: "one" } })
      .mockResolvedValueOnce({ ok: false, stage: "preview", error: { code: "second", message: "two" } });
    const controller = createStartupController(container, makeIO(run));
    await controller.start();

    container.querySelector<HTMLButtonElement>('[data-action="startup-retry"]')!.click();
    await vi.runAllTimersAsync();

    expect(container.textContent).toContain("ZeroRodCAD could not load the initial model.");
    // Show Details must reflect the NEW failure, not the first one — the
    // retry render tears down and rebuilds the error block from scratch.
    container.querySelector<HTMLButtonElement>('[data-action="startup-details"]')!.click();
    expect(container.querySelector(".startup-error-detail")?.textContent).toBe("second: two");
  });

  it("start() called exactly once from app init produces exactly one io.run() call", async () => {
    const run = vi.fn<StartupIO["run"]>().mockResolvedValue({ ok: true });
    const controller = createStartupController(container, makeIO(run));

    await controller.start();

    expect(run).toHaveBeenCalledTimes(1);
  });

  it("dispose() clears a pending 'Preparing…' timer without throwing", async () => {
    const io = makeIO(() => new Promise(() => {})); // never resolves
    const controller = createStartupController(container, io);
    void controller.start();

    expect(() => controller.dispose()).not.toThrow();
    // The timer must actually be cleared — advancing time afterward must
    // not render "Preparing…" into a container nothing owns anymore.
    await vi.advanceTimersByTimeAsync(1000);
    expect(container.textContent).not.toContain("Preparing");
  });
});
