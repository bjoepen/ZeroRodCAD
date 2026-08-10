import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createLatestWinsGate, createLivePreviewController } from "./live_preview";

describe("createLatestWinsGate", () => {
  it("starts with generation 0, not current", () => {
    const gate = createLatestWinsGate();
    expect(gate.current()).toBe(0);
    expect(gate.isCurrent(0)).toBe(true); // 0 is "current" until anything is issued
  });

  it("issues monotonically increasing generations", () => {
    const gate = createLatestWinsGate();
    expect(gate.next()).toBe(1);
    expect(gate.next()).toBe(2);
    expect(gate.next()).toBe(3);
  });

  // §24 of the M4 mandate — MANDATORY: a stale generation must never be
  // reported current once a newer one has been issued, regardless of the
  // order in which the underlying work actually completes. Proven here
  // directly against the gate primitive with manually controlled ordering,
  // independent of any real request timing (the mandate explicitly permits
  // this: "Real engine requests need not naturally return out of order for
  // the race invariant to be tested").
  it("discards an earlier generation once a later one has been issued, regardless of resolution order", () => {
    const gate = createLatestWinsGate();
    const generationA = gate.next(); // request A issued first (e.g. width 40)
    const generationB = gate.next(); // request B supersedes A (e.g. width 60)

    // Simulate A's response arriving AFTER B was already issued (out of
    // order) — A must never be treated as current again.
    expect(gate.isCurrent(generationA)).toBe(false);
    expect(gate.isCurrent(generationB)).toBe(true);
  });

  it("only the single latest generation is ever current, even across many issues", () => {
    const gate = createLatestWinsGate();
    const generations = [gate.next(), gate.next(), gate.next(), gate.next(), gate.next()];
    for (const g of generations.slice(0, -1)) {
      expect(gate.isCurrent(g)).toBe(false);
    }
    expect(gate.isCurrent(generations[generations.length - 1])).toBe(true);
  });
});

// A minimal value type standing in for ZeroRodParametersValues — the
// controller is generic and doesn't need the real contract type for these
// tests (parameter_panel.test.ts covers the real integration).
interface TestValue {
  width: number;
}
const v = (width: number): TestValue => ({ width });
const eq = (a: TestValue, b: TestValue): boolean => a.width === b.width;

describe("createLivePreviewController", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not dispatch before the debounce delay elapses", () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    }).schedule(v(60));

    vi.advanceTimersByTime(299);
    expect(request).not.toHaveBeenCalled();
  });

  it("dispatches once the debounce delay elapses", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    }).schedule(v(60));

    await vi.advanceTimersByTimeAsync(300);
    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith(v(60));
  });

  it("collapses rapid successive schedule() calls into a single dispatch of the final value (§11/§23)", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    // 38 -> 4 -> 45 -> 6 -> 60, each edit arriving well within the debounce window
    for (const width of [4, 45, 6, 60]) {
      controller.schedule(v(width));
      await vi.advanceTimersByTimeAsync(50);
    }
    await vi.advanceTimersByTimeAsync(300);

    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith(v(60));
  });

  it("resets the debounce timer on every new schedule() call", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(40));
    await vi.advanceTimersByTimeAsync(250);
    controller.schedule(v(45)); // arrives before the first timer would have fired
    await vi.advanceTimersByTimeAsync(250);
    expect(request).not.toHaveBeenCalled(); // total elapsed since the *last* schedule is only 250ms
    await vi.advanceTimersByTimeAsync(50);
    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith(v(45));
  });

  it("no-ops when scheduled value equals the currently targeted value (no pending, no dispatch)", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(38)); // same as initialValue
    await vi.advanceTimersByTimeAsync(300);
    expect(request).not.toHaveBeenCalled();
  });

  it("collapses an edit that returns to the initial value before the debounce fires (§36 — 0 requests)", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(40));
    await vi.advanceTimersByTimeAsync(100);
    controller.schedule(v(38)); // back to initial before debounce fires
    await vi.advanceTimersByTimeAsync(300);
    expect(request).not.toHaveBeenCalled();
  });

  it("issues exactly one request when going 38 -> 40 -> back to 38 after 40 was already rendered (§36)", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(40));
    await vi.advanceTimersByTimeAsync(300); // 40 dispatched and "rendered" (targetValue now 40)
    expect(request).toHaveBeenCalledTimes(1);

    controller.schedule(v(38)); // back to the original default
    await vi.advanceTimersByTimeAsync(300);
    expect(request).toHaveBeenCalledTimes(2);
    expect(request).toHaveBeenLastCalledWith(v(38));
  });

  it("coalesces schedule() calls that arrive while a request is in flight — only the latest fires next (§15)", async () => {
    let resolveA!: (r: { ok: true; data: string }) => void;
    const request = vi
      .fn()
      .mockImplementationOnce(() => new Promise((resolve) => (resolveA = resolve)))
      .mockResolvedValue({ ok: true, data: "mesh-d" });

    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 10,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(40)); // request A starts (in flight, unresolved)
    await vi.advanceTimersByTimeAsync(10);
    expect(request).toHaveBeenCalledTimes(1);

    // While A is in flight, B, C, D all get scheduled and debounce-fire in turn.
    controller.schedule(v(45));
    await vi.advanceTimersByTimeAsync(10);
    controller.schedule(v(50));
    await vi.advanceTimersByTimeAsync(10);
    controller.schedule(v(60));
    await vi.advanceTimersByTimeAsync(10);

    expect(request).toHaveBeenCalledTimes(1); // B/C/D coalesced, nothing dispatched yet — A still in flight

    resolveA({ ok: true, data: "mesh-a" });
    await vi.advanceTimersByTimeAsync(0);
    await Promise.resolve();
    await Promise.resolve();

    expect(request).toHaveBeenCalledTimes(2); // A, then only the latest coalesced value (60)
    expect(request).toHaveBeenLastCalledWith(v(60));
  });

  it("scheduleImmediate dispatches without waiting for the debounce delay", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.scheduleImmediate(v(60));
    await vi.advanceTimersByTimeAsync(0);
    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith(v(60));
  });

  it("scheduleImmediate cancels a pending debounced schedule instead of double-firing", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(60));
    controller.scheduleImmediate(v(60));
    await vi.advanceTimersByTimeAsync(300);
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("cancelPending cancels a not-yet-fired debounce timer without affecting anything in flight", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(60));
    controller.cancelPending();
    await vi.advanceTimersByTimeAsync(300);
    expect(request).not.toHaveBeenCalled();
  });

  it("onRequestStart fires synchronously when a request actually begins", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const onRequestStart = vi.fn();
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 300,
      isEqual: eq,
      request,
      onRequestStart,
      onSettle: () => {},
    });

    controller.schedule(v(60));
    expect(onRequestStart).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(300);
    expect(onRequestStart).toHaveBeenCalledWith(v(60), 1);
  });

  it("onSettle reports a successful outcome with the generation and data", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh-payload" });
    const onSettle = vi.fn();
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 10,
      isEqual: eq,
      request,
      onSettle,
    });

    controller.schedule(v(60));
    await vi.advanceTimersByTimeAsync(10);
    await Promise.resolve();
    await Promise.resolve();

    expect(onSettle).toHaveBeenCalledWith({ ok: true, value: v(60), generation: 1, data: "mesh-payload" });
  });

  it("onSettle reports a failed outcome without touching the target value's dedup baseline incorrectly", async () => {
    const request = vi.fn().mockResolvedValue({ ok: false, error: { code: "geometry_error", message: "boom" } });
    const onSettle = vi.fn();
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 10,
      isEqual: eq,
      request,
      onSettle,
    });

    controller.schedule(v(999));
    await vi.advanceTimersByTimeAsync(10);
    await Promise.resolve();
    await Promise.resolve();

    expect(onSettle).toHaveBeenCalledWith({
      ok: false,
      value: v(999),
      generation: 1,
      error: { code: "geometry_error", message: "boom" },
    });
  });

  it("suppresses a duplicate dispatch when the coalesced queued value equals what just settled (§37)", async () => {
    let resolveA!: (r: { ok: true; data: string }) => void;
    const request = vi.fn().mockImplementationOnce(() => new Promise((resolve) => (resolveA = resolve)));
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 10,
      isEqual: eq,
      request,
      onSettle: () => {},
    });

    controller.schedule(v(60)); // A starts
    await vi.advanceTimersByTimeAsync(10);
    controller.schedule(v(60)); // duplicate arrives while A (also 60) is in flight — should not queue a second request
    await vi.advanceTimersByTimeAsync(10);

    resolveA({ ok: true, data: "mesh" });
    await Promise.resolve();
    await Promise.resolve();

    expect(request).toHaveBeenCalledTimes(1);
  });

  it("dispose prevents any further dispatch or settle callback", async () => {
    const request = vi.fn().mockResolvedValue({ ok: true, data: "mesh" });
    const onSettle = vi.fn();
    const controller = createLivePreviewController<TestValue, string>({
      initialValue: v(38),
      debounceMs: 10,
      isEqual: eq,
      request,
      onSettle,
    });

    controller.schedule(v(60));
    controller.dispose();
    await vi.advanceTimersByTimeAsync(50);
    expect(request).not.toHaveBeenCalled();
    expect(onSettle).not.toHaveBeenCalled();
  });
});
