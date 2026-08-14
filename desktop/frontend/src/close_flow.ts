// Build 025 M4 — the re-entrancy-safe wrapper around the single shared
// unsaved-changes guard (§7-10 of the mandate: "ONE unsaved-changes
// decision model"). Extracted out of `main.ts` (which has top-level side
// effects on import and has never been unit-tested directly in this
// project — see e.g. preview.ts's own module doc comment on the same
// convention) purely so this specific piece — the actual safety-critical
// part of this milestone — is directly testable: mock `confirmQuit`, drive
// the returned handler with synthetic close events, assert exactly one
// guard decision runs even when two native close triggers (the red button
// and Cmd+Q/menu Quit, both now producing the identical
// `WindowEvent::CloseRequested`) overlap.
//
// Where the "two overlapping close attempts" scenario actually comes from:
// Build 025 M1's red close button and Build 025 M4's native Quit menu item
// (`desktop/src-tauri/src/menu.rs`) both resume through
// `WebviewWindow::close()`, so each produces its own, independent
// `WindowEvent::CloseRequested` — Tauri's own `onCloseRequested` wrapper
// (`@tauri-apps/api/window`) does not coalesce them. Without this wrapper,
// pressing Cmd+Q twice (or Cmd+Q while the red-close guard is already
// showing, or vice versa) would call `confirmQuit()` a second time
// concurrently, stacking a second Save/Discard/Cancel dialog on the first.

export interface CloseGuard {
  /** The single shared decision function — `project_panel.ts`'s
   * `confirmQuit()`, unmodified. This module never re-implements or
   * duplicates its logic (§9 of the mandate). */
  confirmQuit: () => Promise<boolean>;
}

export interface CloseRequestedEventLike {
  preventDefault: () => void;
}

/** Returns a handler suitable for `getCurrentWindow().onCloseRequested(...)`.
 * While a decision is already in flight, any further close event this
 * handler receives is cancelled immediately (`preventDefault()`) rather
 * than starting a second guard — the in-flight decision's own eventual
 * "proceed" is what actually closes the window, via its own event's
 * fallthrough. Once a decision fully settles, the next close attempt
 * starts a genuinely fresh one. */
export function createCloseRequestHandler(
  guard: CloseGuard,
): (event: CloseRequestedEventLike) => Promise<void> {
  let inFlight: Promise<boolean> | null = null;

  return async function handleCloseRequested(event: CloseRequestedEventLike): Promise<void> {
    if (inFlight) {
      event.preventDefault();
      return;
    }
    const decision = guard.confirmQuit();
    inFlight = decision;
    try {
      const proceed = await decision;
      if (!proceed) {
        event.preventDefault();
      }
    } finally {
      inFlight = null;
    }
  };
}
