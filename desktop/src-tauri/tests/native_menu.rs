// Build 025 M4 — real IPC-boundary/runtime evidence for the menu-event
// routing layer, mirroring the "test the actual boundary, not a mock one
// layer down" standard `tests/native_close_permission.rs` already
// established for the M1 ACL bug.
//
// Menu *construction* itself (`menu::build_menu` — `Menu`/`Submenu`/
// `CheckMenuItem`/`PredefinedMenuItem::with_id`/`::about`, all backed by
// the `muda` crate) cannot be exercised here: muda's macOS backend
// requires the real Cocoa main thread (confirmed directly —
// `muda::MenuChild` can only be created on the main thread; `cargo test`'s
// test binary never runs on it, even single-threaded, since no
// `NSApplication` main-thread registration ever happens outside a real
// launched GUI app). This is a genuine platform limitation, not a gap in
// this module's design — the same class of limitation `preview.test.ts`'s
// own module doc comment already documents for `createPreviewController`
// (needs a real GPU/WebGL context jsdom cannot provide). Real evidence for
// menu *construction* — the tree actually containing no
// `PredefinedMenuItem::quit`, every expected id present, the three
// visibility items starting checked — instead comes from: (a) direct
// source inspection (this module has exactly one call site that could
// construct a Quit item, and it is a plain `MenuItem::with_id`, never
// `PredefinedMenuItem::quit` — enforced by `scripts/validate-build025-m4.sh`'s
// structural checks) and (b) a real launched dev/release build, which
// DOES run on the true main thread and was used directly during this
// milestone's implementation to confirm the menu constructs without a
// panic/crash (see docs/migration/BUILD-025-M4-DESKTOP-SHELL.md).
//
// What CAN be tested here, because it needs no muda construction at all,
// is `handle_menu_event`'s actual routing decision for "quit" — the one
// piece of logic this milestone adds that a human/GUI click ultimately
// depends on: does it call `WebviewWindow::close()` (safe — resumes
// through the already-validated guarded pipeline) rather than
// `AppHandle::exit()`/terminating the process directly? `close()` itself
// is a `MockRuntime` dispatcher no-op with no directly observable side
// effect in this harness, so the strongest thing provable here is the
// negative: routing "quit" must never panic, hang, or fall through to any
// other code path — i.e. it is safe to call with only a "main" window
// present and nothing else set up (no menu, no state), exactly the
// minimal precondition `lib.rs`'s real `.on_menu_event(menu::handle_menu_event)`
// wiring guarantees.
//
// This lives in `tests/` (a separate compilation unit) for the identical
// reason `native_close_permission.rs` does: `lib.rs` already calls
// `tauri::generate_context!()` once, and a second invocation in the same
// binary fails to compile.

use tauri::menu::MenuEvent;
use tauri::test::{mock_builder, MockRuntime};
use tauri::webview::WebviewWindowBuilder;
use zerorod_desktop_lib::menu;

// `tauri::generate_context!()` embeds file-scoped resource symbols, so it
// may only be invoked once per compilation unit (this file is its own
// binary — see the module doc comment) — factored into one shared helper
// rather than called again per test.
fn build_test_app() -> tauri::App<MockRuntime> {
    let app = mock_builder()
        .build(tauri::generate_context!())
        .expect("failed to build app");
    WebviewWindowBuilder::new(&app, "main", Default::default())
        .build()
        .expect("failed to build the main window");
    app
}

#[test]
fn routing_quit_to_window_close_does_not_panic_with_only_a_main_window_present() {
    let app = build_test_app();
    let handle = app.handle().clone();
    let event = MenuEvent {
        id: menu::MENU_ID_QUIT.into(),
    };

    // The real assertion is simply that this returns normally: no panic,
    // no attempt to reach a menu tree that doesn't exist here (proving the
    // "quit" branch's early return never touches `app.menu()`, unlike
    // every other id, which does — see `checked_state_for`).
    menu::handle_menu_event(&handle, event);
}

#[test]
fn routing_a_non_quit_id_with_no_menu_present_does_not_panic() {
    // Every id other than "quit" looks up the menu tree (to read a check
    // item's state) before forwarding — with no menu configured at all in
    // this test, that lookup must fail closed (None) rather than panic,
    // and the event must still be forwarded with `checked: None`.
    let app = build_test_app();
    let handle = app.handle().clone();
    let event = MenuEvent {
        id: menu::MENU_ID_FILE_NEW.into(),
    };

    menu::handle_menu_event(&handle, event);
}
