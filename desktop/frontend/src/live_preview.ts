// Build 023 M4 — debounced live-preview scheduling. Owns *when* and
// *whether* to issue a geometry request for a given valid parameter value,
// and which result is allowed to reach the caller — no DOM, no Three.js, no
// sidecar-specific knowledge (parameter_panel.ts wires this to
// preview.ts's fetchPreview/commitPreview). Two concerns, deliberately kept
// separable:
//
//   1. `createLatestWinsGate` — the minimal stale-response-protection
//      primitive (§13/§26 of the M4 mandate): a monotonically increasing
//      generation counter where only the highest-issued generation is ever
//      "current." Directly unit-testable with manually out-of-order
//      resolution, independent of whether the real transport could ever
//      actually reorder responses (it can't, in this app's design — see
//      "Concurrency model" below) — exactly what the mandate's §24
//      explicitly allows ("Real engine requests need not naturally return
//      out of order for the race invariant to be tested").
//   2. `createLivePreviewController` — debounce + in-flight coalescing +
//      duplicate suppression, built on top of the gate above.
//
// Concurrency model: this controller never dispatches two requests at once
// (`inFlight` blocks a second `startRequest` until the first settles) —
// deliberately, to avoid sending a request for an already-superseded draft
// while a prior one is still running (§15/§33 of the mandate: minimize
// engine load, coalesce rather than queue every intermediate state). Because
// of that serialization, `createLivePreviewController`'s own gate can never
// actually observe a stale generation through normal `schedule()` calls —
// the mandatory out-of-order proof therefore lives at the `createLatestWinsGate`
// level (live_preview.test.ts), which is deliberately transport-agnostic
// and exercises the exact invariant the mandate describes.

export interface LatestWinsGate {
  /** Issues and returns a new generation number, becoming the new "latest
   * desired" state. */
  next(): number;
  /** True iff `generation` is still the highest one ever issued — i.e. no
   * newer `next()` call has happened since. */
  isCurrent(generation: number): boolean;
  /** The most recently issued generation (0 if `next()` was never called) —
   * a read-only peek, does not itself issue a new generation. */
  current(): number;
}

export function createLatestWinsGate(): LatestWinsGate {
  let generation = 0;
  return {
    next: () => (generation += 1),
    isCurrent: (generation_) => generation_ === generation,
    current: () => generation,
  };
}

export type LivePreviewOutcome<T, R> =
  | { ok: true; value: T; generation: number; data: R }
  | { ok: false; value: T; generation: number; error: unknown };

export interface LivePreviewControllerConfig<T, R> {
  /** The value already represented (or being requested) when the controller
   * is constructed — e.g. the canonical defaults just loaded. Seeds the
   * dedup baseline so "edit away and back before the debounce fires" is
   * recognized as a no-op from the very first edit (§36 of the mandate). */
  initialValue: T;
  debounceMs: number;
  isEqual: (a: T, b: T) => boolean;
  request: (value: T) => Promise<{ ok: true; data: R } | { ok: false; error: unknown }>;
  /** Fires synchronously the moment a request actually starts (debounce
   * elapsed, or `scheduleImmediate`) — before `request()` is even called. */
  onRequestStart?: (value: T, generation: number) => void;
  /** Fires once `request()` settles, but ONLY when `generation` is still
   * current per the latest-wins gate (§13) — a response for a superseded
   * generation is silently discarded before this ever fires. In this
   * controller's serialized design that discard path is never actually
   * exercised (see the module doc's "Concurrency model"); the gate itself
   * is proven directly in live_preview.test.ts. */
  onSettle: (outcome: LivePreviewOutcome<T, R>) => void;
}

export interface LivePreviewController<T> {
  /** Debounced schedule — cancels any not-yet-fired pending timer and
   * replaces it. No-ops entirely (cancels any pending timer, doesn't touch
   * an in-flight request) if `value` already equals what's currently
   * targeted (in-flight, queued, or just-dispatched) — §36/§37 of the
   * mandate. */
  schedule(value: T): void;
  /** Cancels any pending (not yet fired) debounce timer — never touches an
   * in-flight request, which is left to finish and (if successful) still
   * update state, since it was legitimately dispatched from a valid draft
   * (§20 of the mandate: an in-flight result still represents "the last
   * valid state," even if the draft has since become invalid). */
  cancelPending(): void;
  /** Cancels any pending debounce timer and dispatches `value` right away
   * (still subject to in-flight coalescing) — the explicit-Apply path
   * (§16/§22 of the mandate). Unlike `schedule`, this does NOT dedup
   * against the last-dispatched value, so it can be used to retry after an
   * error even when nothing about the value itself has changed; callers
   * are expected to gate *whether* to call this on their own
   * already-successfully-represented check (parameter_panel.ts uses
   * `accepted`, not this controller's internal dedup, for that). */
  scheduleImmediate(value: T): void;
  dispose(): void;
  /** Test/debug hook. */
  getGeneration(): number;
}

export function createLivePreviewController<T, R>(
  config: LivePreviewControllerConfig<T, R>,
): LivePreviewController<T> {
  const gate = createLatestWinsGate();

  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  let pendingValue: T | null = null;
  let inFlight = false;
  let queuedValue: T | null = null;
  let targetValue: T = config.initialValue;
  let disposed = false;

  function clearTimer(): void {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  }

  function schedule(value: T): void {
    if (disposed) return;
    if (config.isEqual(value, targetValue)) {
      clearTimer();
      pendingValue = null;
      return;
    }
    pendingValue = value;
    clearTimer();
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      const fired = pendingValue;
      pendingValue = null;
      if (fired !== null) dispatch(fired);
    }, config.debounceMs);
  }

  function cancelPending(): void {
    clearTimer();
    pendingValue = null;
  }

  function scheduleImmediate(value: T): void {
    if (disposed) return;
    clearTimer();
    pendingValue = null;
    dispatch(value);
  }

  function dispatch(value: T): void {
    if (inFlight) {
      queuedValue = value;
      return;
    }
    startRequest(value);
  }

  function startRequest(value: T): void {
    inFlight = true;
    targetValue = value;
    const generation = gate.next();
    config.onRequestStart?.(value, generation);

    config.request(value).then((result) => {
      inFlight = false;
      if (!disposed && gate.isCurrent(generation)) {
        if (result.ok) {
          config.onSettle({ ok: true, value, generation, data: result.data });
        } else {
          config.onSettle({ ok: false, value, generation, error: result.error });
        }
      }
      if (!disposed && queuedValue !== null) {
        const next = queuedValue;
        queuedValue = null;
        if (!config.isEqual(next, targetValue)) {
          startRequest(next);
        }
      }
    });
  }

  function dispose(): void {
    disposed = true;
    clearTimer();
    pendingValue = null;
    queuedValue = null;
  }

  return {
    schedule,
    cancelPending,
    scheduleImmediate,
    dispose,
    getGeneration: () => gate.current(),
  };
}
