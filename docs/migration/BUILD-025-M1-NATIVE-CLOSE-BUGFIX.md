# Build 025 / Milestone 1 — Native Close/Quit Bugfix

The Project Owner reported that the freshly built `ZeroRodCAD-Build025-M1.app` could not be closed
via the red macOS traffic-light close button — clicking it did nothing. Quitting via the App
menu/⌘Q worked. Human Validation was correctly withheld pending a fix.

## Root cause

**Category: missing WebView capability (ACL) grant — not an application-logic defect.**

`desktop/frontend/src/main.ts` already implements exactly the pattern Tauri v2 documents for a
guarded window close:

```ts
void getCurrentWindow().onCloseRequested(async (event) => {
  const proceed = await projectPanel.confirmQuit();
  if (!proceed) {
    event.preventDefault();
  }
});
```

`projectPanel.confirmQuit()` (`desktop/frontend/src/project_panel.ts`) resolves `true` immediately
for a clean project, or shows the Save/Discard/Cancel guard for a dirty one — this state machine
was already correct and already had full test coverage in `project_panel.test.ts` (clean, Cancel,
Discard, successful Save, failed Save). Nothing here was the bug.

The actual defect is two Tauri-internal mechanisms interacting:

1. **Native close is deferred automatically once a JS listener exists.** Tauri's own
   `on_window_event` handler (`tauri-2.11.5/src/manager/window.rs`) does this on every native
   `WindowEvent::CloseRequested`:
   ```rust
   WindowEvent::CloseRequested { api } => {
     if window.has_js_listener(WINDOW_CLOSE_REQUESTED_EVENT) {
       api.prevent_close();
     }
     window.emit_to_window(WINDOW_CLOSE_REQUESTED_EVENT, &())?;
   }
   ```
   Because `main.ts` registers a `close-requested` listener, `prevent_close()` fires synchronously
   on every native close attempt (giving the async JS guard time to run), and the window is only
   actually destroyed once the JS side explicitly calls back in.
2. **The JS SDK resumes the close via an `invoke()` call, not automatically.** The `onCloseRequested`
   wrapper in `@tauri-apps/api/window` (installed dependency, unmodified) is:
   ```js
   async onCloseRequested(handler) {
     return this.listen(TauriEvent.WINDOW_CLOSE_REQUESTED, async (event) => {
       const evt = new CloseRequestedEvent(event);
       await handler(evt);
       if (!evt.isPreventDefault()) {
         await this.destroy();      // <-- invoke('plugin:window|destroy', ...)
       }
     });
   }
   ```
   When the guard resolves "proceed" (no `preventDefault()`), this fallthrough calls `destroy()`,
   which invokes the Tauri core command `plugin:window|destroy`. Tauri gates that command behind
   the permission `core:window:allow-destroy`.

`desktop/src-tauri/capabilities/main-capability.json` granted only `core:default`, and
`core:default`'s expansion (`core:window:default`, per
`desktop/src-tauri/gen/schemas/desktop-schema.json`) does **not** include `allow-close` or
`allow-destroy` — only read-only window queries (`is_closable`, `is_visible`, `title`, …). So the
`destroy()` call was silently rejected by Tauri's ACL, every single time, for every project state
(clean or dirty) — not just the dirty/guarded case. Native close had already been deferred
(step 1), and the one call that was supposed to resume it never had permission to run: the window
simply never closed. Confirmed with the exact rejection message reproduced by the regression test
below:

```
window.destroy not allowed. Permissions associated with this command: core:window:allow-destroy
```

- Source file: `desktop/src-tauri/capabilities/main-capability.json`
- Nothing in `desktop/frontend/src/main.ts` or `desktop/frontend/src/project_panel.ts` needed to
  change.

## Fix

One line: add `core:window:allow-destroy` to `main-capability.json`'s permission list — the
minimal grant `destroy()` actually needs (not the broader `core:window:allow-close`, which is
unused here and would also re-emit `CloseRequested`, unlike `destroy()`, which "does not emit any
events and force close[s] the window instead" per its own Tauri doc comment — the JS SDK's choice
of `destroy()` over `close()` in its fallthrough is deliberate, and is exactly why this app's close
flow has no recursive-guard risk to begin with).

## Regression protection

Real Tauri command/event boundaries are tested where feasible, per Build 024 M2 policy (see the
`feedback-tauri-command-arg-casing` project memory — the analogous prior bug that also went
undetected because only a mocked `invoke()` was ever exercised). A mocked `invoke()` cannot catch
an ACL rejection at all, since ACL enforcement lives entirely on the Rust side.

- `desktop/src-tauri/tests/native_close_permission.rs` (new, an integration test — a separate
  compilation unit, because `lib.rs` already calls `tauri::generate_context!()` once to build the
  real app, and a second invocation in the same binary fails to compile with a duplicate
  `_EMBED_INFO_PLIST` symbol): builds a real `App` from this project's actual
  `tauri.conf.json`/`capabilities/*.json` (`tauri::generate_context!()`, not the synthetic
  `mock_context()` the existing `ipc_argument_binding` tests use — that distinction matters here,
  since this test's entire point is to exercise the real capability grant) and dispatches a real
  `plugin:window|destroy` IPC request for the `main` window, asserting it is now allowed. Verified
  to actually catch the regression: reverting only the capability-file change reproduces the exact
  `window.destroy not allowed. Permissions associated with this command: core:window:allow-destroy`
  error from this test.
- `desktop/frontend`'s existing `project_panel.test.ts` coverage of `confirmQuit()` (clean,
  Cancel, Discard, successful Save, failed Save, Save-As cancellation, uncommitted-draft guard)
  was already complete and required no changes — the bug never lived in that logic. All 263
  existing frontend tests still pass unchanged.

## A second, pre-existing gap found while tracing this (explicitly NOT fixed here)

Tracing "why does menu Quit succeed while the red button doesn't" (per the mandate's own §5)
surfaced a real, separate gap: macOS's default "Quit ZeroRodCAD" application-menu item — Tauri
auto-generates this menu because no custom menu has been built yet (native menus are Build 025
M4's job) — is a native `PredefinedMenuItem::quit`. Confirmed directly in the `muda` crate
(`muda-0.19.3/src/platform_impl/macos/mod.rs`): its action selector is wired straight to AppKit's
`terminate:`, and `tao` (`tao-0.35.3/src/platform_impl/macos/app_delegate.rs`) implements no
`applicationShouldTerminate:` override. So native Quit bypasses `WindowEvent::CloseRequested` (and
therefore the entire JS unsaved-changes guard) completely — it does not run the same protection
flow the red button now correctly does. This is **not a regression from this fix**; it predates
this corrective task and was already true in the build the Project Owner tested (they simply
didn't hit it, since "menu Quit works" in the sense that it does successfully quit).

Fixing it properly would mean replacing Tauri's implicit default menu with an explicit one whose
Quit item is a normal (non-predefined) `MenuItem` routed through `window.close()` — a genuine,
if small, Tauri menu-integration change, which sits on the wrong side of this mandate's explicit
"do NOT add native menus" scope freeze (§3), reserved for Build 025 M4. Per an explicit Project
Owner decision during this fix, **this task fixes the red close button only**; the menu-Quit gap is
documented here and in `docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md`'s checklist (so a human
tester doesn't mistake the known gap for a new regression) and should be closed as part of Build
025 M4's native-menu work, not silently forgotten.

One related concern was checked and is **not** an issue: whether native Quit orphans the Python
sidecar, since it bypasses `RunEvent::ExitRequested` (`lib.rs`'s only sidecar-kill hook — confirmed
via `tauri-runtime-wry-2.11.4/src/lib.rs`, native Quit only ever reaches `RunEvent::Exit`, fired far
too late in `applicationWillTerminate:` for a meaningful kill to help). Verified directly against a
real built `.app` (`cargo tauri build --debug`, launched, sent a real `quit` Apple Event via
`osascript`): the sidecar process exits together with the app regardless, because
`zerorod_sidecar/main.py`'s persistent request loop already treats stdin EOF as an implicit
shutdown ("the Rust engine manager closing stdin is a normal cleanup path") — an independent,
already-existing Build 022 safety net that holds regardless of which Rust-level exit path (or
none) runs. Orphan count was 0 in this direct test.

## Scope discipline

Nothing else about Build 025 M1's project-persistence functionality was touched. No M2 work
(Diagnostics relocation, native menus, automatic initial preview, startup-failure UX) was started.
`project.py` was not touched.
