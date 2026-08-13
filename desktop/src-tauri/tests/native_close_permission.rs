// Build 025 M1 native-close corrective fix — real ACL-boundary regression
// test for the actual red-macOS-close-button defect a Project Owner hit in
// Human Validation.
//
// Root cause: the frontend's documented `onCloseRequested` pattern
// (desktop/frontend/src/main.ts) resolves a "proceed" close by relying on
// the Tauri JS SDK's own `onCloseRequested` wrapper, which — once the app's
// unsaved-changes guard resolves without calling `event.preventDefault()` —
// falls through to `this.destroy()` (`@tauri-apps/api/window`), invoking
// `plugin:window|destroy`. Before this fix, `capabilities/main-capability.json`
// granted only `core:default` (-> `core:window:default`, which does NOT
// include `allow-close`/`allow-destroy` — confirmed against
// `desktop/src-tauri/gen/schemas/desktop-schema.json`), so that call was
// silently ACL-rejected. Meanwhile Tauri's own native window-event handler
// (`tauri::WindowEvent::CloseRequested`, `tauri-2.11.5/src/manager/window.rs`)
// already calls the Rust-side `prevent_close()` synchronously whenever *any*
// JS close-requested listener is registered (so the async guard has time to
// run) — so the native close was correctly deferred, but the deferred
// `destroy()` call that was supposed to resume it never had permission to
// run, and the window simply never closed.
//
// This dispatches the real command name through the real, project
// capability file (`tauri::generate_context!()`, not `mock_context()`) to
// prove the grant is actually in effect — the same class of "real IPC
// boundary, not a mocked `invoke()`" test `commands.rs`'s
// `ipc_argument_binding` module uses for the analogous Build 024 M2 bug (see
// the `feedback-tauri-command-arg-casing` project memory).
//
// This lives in `tests/` (a separate compilation unit), not in
// `src/commands.rs`'s own `#[cfg(test)]` module, because `lib.rs` already
// calls `tauri::generate_context!()` once to build the real app — a second
// invocation in the same crate/binary fails to compile
// (`symbol '_EMBED_INFO_PLIST' is already defined`), since the macro embeds
// file-scoped resource symbols. A `tests/*.rs` integration test is its own
// binary, so this is the one invocation in that binary.

use tauri::ipc::{CallbackFn, InvokeBody};
use tauri::test::{get_ipc_response, mock_builder, INVOKE_KEY};
use tauri::webview::InvokeRequest;
use tauri::WebviewWindowBuilder;

#[test]
fn window_destroy_is_permitted_for_the_main_window() {
    let app = mock_builder()
        .build(tauri::generate_context!())
        .expect("failed to build app with the real project capabilities");
    let webview = WebviewWindowBuilder::new(&app, "main", Default::default())
        .build()
        .unwrap();

    let request = InvokeRequest {
        cmd: "plugin:window|destroy".into(),
        callback: CallbackFn(0),
        error: CallbackFn(1),
        // Same reasoning as `commands.rs`'s `ipc_argument_binding::dispatch`:
        // `tauri://localhost`, not `http://tauri.localhost`, is what
        // `MockRuntime` recognizes as the local origin that ACL capability
        // grants actually apply to.
        url: "tauri://localhost".parse().unwrap(),
        body: InvokeBody::from(serde_json::json!({"label": "main"})),
        headers: Default::default(),
        invoke_key: INVOKE_KEY.to_string(),
    };

    get_ipc_response(&webview, request).expect(
        "plugin:window|destroy must be allowed for the main window \
         (core:window:allow-destroy) — without it, the frontend's \
         onCloseRequested fallthrough can never actually close the window",
    );
}
