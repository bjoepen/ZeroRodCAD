import { describe, expect, it, vi } from "vitest";
import { createCloseRequestHandler, type CloseGuard, type CloseRequestedEventLike } from "./close_flow";

function fakeEvent(): CloseRequestedEventLike & { preventDefault: ReturnType<typeof vi.fn<() => void>> } {
  return { preventDefault: vi.fn() };
}

describe("createCloseRequestHandler (Build 025 M4, §7-10 of the mandate)", () => {
  it("clean project: confirmQuit resolves true, preventDefault is never called (window closes)", async () => {
    const confirmQuit = vi.fn<CloseGuard["confirmQuit"]>().mockResolvedValue(true);
    const handler = createCloseRequestHandler({ confirmQuit });
    const event = fakeEvent();

    await handler(event);

    expect(confirmQuit).toHaveBeenCalledTimes(1);
    expect(event.preventDefault).not.toHaveBeenCalled();
  });

  it("Cancel: confirmQuit resolves false, preventDefault is called (window stays open)", async () => {
    const confirmQuit = vi.fn<CloseGuard["confirmQuit"]>().mockResolvedValue(false);
    const handler = createCloseRequestHandler({ confirmQuit });
    const event = fakeEvent();

    await handler(event);

    expect(event.preventDefault).toHaveBeenCalledTimes(1);
  });

  it("never duplicates confirmQuit logic itself — this module only calls the given guard", () => {
    const confirmQuit = vi.fn<CloseGuard["confirmQuit"]>().mockResolvedValue(true);
    const guard: CloseGuard = { confirmQuit };
    createCloseRequestHandler(guard);
    expect(confirmQuit).not.toHaveBeenCalled(); // not called until an event arrives
  });

  it("re-entrancy: a second close event arriving while the first is still pending is cancelled immediately, without a second confirmQuit call", async () => {
    let resolveFirst!: (value: boolean) => void;
    const confirmQuit = vi.fn<CloseGuard["confirmQuit"]>().mockReturnValueOnce(new Promise<boolean>((resolve) => (resolveFirst = resolve)));
    const handler = createCloseRequestHandler({ confirmQuit });

    const firstEvent = fakeEvent();
    const firstPromise = handler(firstEvent); // starts the guard, does not resolve yet

    const secondEvent = fakeEvent();
    await handler(secondEvent); // a second close trigger (e.g. Cmd+Q pressed again) while the first is pending

    // The second attempt must be cancelled immediately — no second dialog.
    expect(secondEvent.preventDefault).toHaveBeenCalledTimes(1);
    expect(confirmQuit).toHaveBeenCalledTimes(1); // still only the one guard decision

    resolveFirst(true);
    await firstPromise;
    expect(firstEvent.preventDefault).not.toHaveBeenCalled(); // the original attempt proceeds
  });

  it("re-entrancy: repeated Cmd+Q (many overlapping attempts) still produces exactly one guard decision", async () => {
    let resolveFirst!: (value: boolean) => void;
    const confirmQuit = vi.fn<CloseGuard["confirmQuit"]>().mockReturnValueOnce(new Promise<boolean>((resolve) => (resolveFirst = resolve)));
    const handler = createCloseRequestHandler({ confirmQuit });

    const events = [fakeEvent(), fakeEvent(), fakeEvent(), fakeEvent()];
    const firstPromise = handler(events[0]);
    await Promise.all(events.slice(1).map((e) => handler(e)));

    expect(confirmQuit).toHaveBeenCalledTimes(1);
    for (const event of events.slice(1)) {
      expect(event.preventDefault).toHaveBeenCalledTimes(1);
    }

    resolveFirst(false);
    await firstPromise;
    expect(events[0].preventDefault).toHaveBeenCalledTimes(1); // Cancel outcome
  });

  it("after a decision fully resolves, the next close attempt starts a genuinely new guard decision", async () => {
    const confirmQuit = vi.fn<CloseGuard["confirmQuit"]>().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const handler = createCloseRequestHandler({ confirmQuit });

    const first = fakeEvent();
    await handler(first); // Cancel

    const second = fakeEvent();
    await handler(second); // a fresh attempt afterward, e.g. the user tries again

    expect(confirmQuit).toHaveBeenCalledTimes(2);
    expect(first.preventDefault).toHaveBeenCalledTimes(1);
    expect(second.preventDefault).not.toHaveBeenCalled();
  });

  it("red close and native Quit share the exact same handler instance, proving there is only one guard, not two", async () => {
    // Simulates §10's "red close while a Cmd+Q guard is active" and vice
    // versa: both entry points call the SAME handler main.ts wires to
    // onCloseRequested — there is no separate confirmNativeQuit/
    // confirmWindowQuit implementation to keep in sync (§9 of the mandate).
    let resolveGuard!: (value: boolean) => void;
    const confirmQuit = vi.fn<CloseGuard["confirmQuit"]>().mockReturnValueOnce(new Promise<boolean>((resolve) => (resolveGuard = resolve)));
    const handler = createCloseRequestHandler({ confirmQuit });

    const redCloseEvent = fakeEvent(); // "triggered by the red button"
    const cmdQEvent = fakeEvent(); // "triggered by Cmd+Q moments later"
    const redClosePromise = handler(redCloseEvent);
    await handler(cmdQEvent);

    expect(confirmQuit).toHaveBeenCalledTimes(1);
    expect(cmdQEvent.preventDefault).toHaveBeenCalledTimes(1);

    resolveGuard(true);
    await redClosePromise;
    expect(redCloseEvent.preventDefault).not.toHaveBeenCalled();
  });
});
