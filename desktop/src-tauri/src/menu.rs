//! Build 025 M4 — the native macOS application menu (§8/§9/§12 of the
//! mandate). This module owns exactly two things: building the menu tree,
//! and routing each menu click to either (a) the one place a native click
//! must be handled in Rust — Quit, which must resume through the existing,
//! already-validated window-close pipeline, never through
//! `AppHandle::exit()`/`std::process::exit()` — or (b) a generic event
//! forwarded to the WebView, where the *real* action (New/Open/Save/Reset
//! View/…) already lives, unmodified, since Build 025 M1-M3. This module
//! contains no project/export/preview decision logic of its own — see the
//! module-level rationale below the `Quit` handling.
//!
//! ## Why Quit routes through `window.close()`, not `app.exit()`
//!
//! Build 025 M1 found (`docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md`)
//! that macOS's *implicit default* menu bar's Quit item is a
//! `PredefinedMenuItem::quit` — confirmed directly in the `muda` crate
//! (`muda-0.19.3/src/platform_impl/macos/mod.rs`,
//! `PredefinedMenuItemType::Quit => Some(sel!(terminate:))`) to be wired
//! straight to AppKit's `terminate:`, bypassing Tauri's window-event
//! pipeline (and therefore the JS unsaved-changes guard) entirely. This
//! module never constructs a `PredefinedMenuItem::quit` — the "Quit
//! ZeroRodCAD" item below is a plain custom `MenuItem` whose click handler
//! calls `WebviewWindow::close()`, which (`tauri-2.11.5/src/window/mod.rs`)
//! "emits `WindowEvent::CloseRequested` first like a user-initiated close
//! request" — i.e. the *exact* same native event the red traffic-light
//! button already produces, all the way down to the same
//! `tauri-runtime-wry` dispatcher call
//! (`Message::Window(id, WindowMessage::Close) => on_close_requested(...)`,
//! confirmed by reading the vendored crate directly). Tauri's own
//! `on_window_event` (`tauri-2.11.5/src/manager/window.rs`) then applies
//! its existing `has_js_listener` → `prevent_close()` logic identically
//! regardless of which of the two produced the event, so
//! `main.ts`'s single `onCloseRequested` handler — and therefore
//! `projectPanel.confirmQuit()`, the one and only unsaved-changes guard —
//! is reached either way. No guard logic is duplicated in Rust (§9 of the
//! mandate): this file never inspects project/dirty state at all.

use tauri::menu::{CheckMenuItem, Menu, MenuEvent, MenuItem, PredefinedMenuItem, Submenu};
use tauri::{AppHandle, Emitter, Manager, Runtime};

use crate::commands::app_info;

/// Menu item IDs the frontend's `native_menu.ts` bridge switches on.
/// `"quit"` is handled entirely here and never forwarded (see the module
/// doc comment) — every other ID is forwarded to the WebView verbatim via
/// the `"menu-action"` event, unchanged, so adding a new menu item never
/// requires touching the routing logic below, only this list and the
/// bridge's switch.
pub const MENU_ID_APP_MENU: &str = "app-menu";
pub const MENU_ID_QUIT: &str = "quit";
pub const MENU_ID_FILE_NEW: &str = "file-new";
pub const MENU_ID_FILE_OPEN: &str = "file-open";
pub const MENU_ID_FILE_SAVE: &str = "file-save";
pub const MENU_ID_FILE_SAVE_AS: &str = "file-save-as";
pub const MENU_ID_FILE_EXPORT: &str = "file-export";
pub const MENU_ID_VIEW_RESET: &str = "view-reset";
pub const MENU_ID_VIEW_BODY: &str = "view-body";
pub const MENU_ID_VIEW_ROD: &str = "view-rod";
pub const MENU_ID_VIEW_STRINGS: &str = "view-strings";
pub const MENU_ID_VIEW_REPORT: &str = "view-report";
pub const MENU_ID_VIEW_DIAGNOSTICS: &str = "view-diagnostics";

/// The Tauri event name `main.ts`'s `native_menu.ts` bridge listens for.
pub const MENU_ACTION_EVENT: &str = "menu-action";

/// The event payload for `MENU_ACTION_EVENT` — `checked` is only present
/// for the three `CheckMenuItem`s (Show Body/Rod/Strings), carrying the
/// item's own post-click state (native toggle already applied by the OS
/// before this handler runs) so the frontend never has to guess/complement
/// a value — it is simply told what is now true (§16 of the mandate: the
/// presentation source of truth stays in the frontend; Rust only reports
/// what the user just clicked).
#[derive(Debug, Clone, serde::Serialize)]
pub struct MenuActionPayload<'a> {
    pub id: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub checked: Option<bool>,
}

/// Builds the full native menu tree. Called from `lib.rs`'s
/// `Builder::menu(...)` — replaces the implicit default menu entirely (no
/// `PredefinedMenuItem::quit`, ever), per §8 of the mandate: "Do not allow
/// the native predefined Quit item to terminate the process before the
/// guard runs."
pub fn build_menu<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<Menu<R>> {
    let info = app_info();
    let about_metadata = tauri::menu::AboutMetadata {
        name: Some(info.name.clone()),
        // §23 of the mandate: About and Diagnostics must never disagree —
        // both derive from this same app_info() call, not a second
        // hardcoded string. See also commands.rs's app_info() doc comment.
        version: Some(format!("{} — Build {} {}", info.version, info.build, info.milestone)),
        ..Default::default()
    };

    // macOS maps the first submenu's items into the application menu and
    // uses the running app's real name for its title regardless of the
    // string given here (confirmed against tauri-2.11.5's own
    // `Menu::default` implementation) — "ZeroRodCAD" is used only as the
    // non-macOS fallback title.
    let app_menu = Submenu::with_id_and_items(
        app,
        "app-menu",
        "ZeroRodCAD",
        true,
        &[
            &PredefinedMenuItem::about(app, Some("About ZeroRodCAD"), Some(about_metadata))?,
            &PredefinedMenuItem::separator(app)?,
            // Deliberately NOT PredefinedMenuItem::quit — see module doc
            // comment. Plain custom item; handle_menu_event routes this id
            // to WebviewWindow::close(), never AppHandle::exit().
            &MenuItem::with_id(app, MENU_ID_QUIT, "Quit ZeroRodCAD", true, Some("CmdOrCtrl+Q"))?,
        ],
    )?;

    let file_menu = Submenu::with_id_and_items(
        app,
        "file",
        "File",
        true,
        &[
            &MenuItem::with_id(app, MENU_ID_FILE_NEW, "New", true, Some("CmdOrCtrl+N"))?,
            &MenuItem::with_id(app, MENU_ID_FILE_OPEN, "Open…", true, Some("CmdOrCtrl+O"))?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, MENU_ID_FILE_SAVE, "Save", true, Some("CmdOrCtrl+S"))?,
            &MenuItem::with_id(
                app,
                MENU_ID_FILE_SAVE_AS,
                "Save As…",
                true,
                Some("Shift+CmdOrCtrl+S"),
            )?,
            &PredefinedMenuItem::separator(app)?,
            // §14 of the mandate: no invented shortcut for Export.
            &MenuItem::with_id(app, MENU_ID_FILE_EXPORT, "Export Model…", true, None::<&str>)?,
        ],
    )?;

    let view_menu = Submenu::with_id_and_items(
        app,
        "view",
        "View",
        true,
        &[
            &MenuItem::with_id(app, MENU_ID_VIEW_RESET, "Reset View", true, None::<&str>)?,
            &PredefinedMenuItem::separator(app)?,
            // §14 of the M3 mandate: default visible — mirrored here as
            // initially checked (§16 of the M4 mandate).
            &CheckMenuItem::with_id(app, MENU_ID_VIEW_BODY, "Show Body", true, true, None::<&str>)?,
            &CheckMenuItem::with_id(app, MENU_ID_VIEW_ROD, "Show Rod", true, true, None::<&str>)?,
            &CheckMenuItem::with_id(
                app,
                MENU_ID_VIEW_STRINGS,
                "Show Strings",
                true,
                true,
                None::<&str>,
            )?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, MENU_ID_VIEW_REPORT, "Instrument Report", true, None::<&str>)?,
            &MenuItem::with_id(app, MENU_ID_VIEW_DIAGNOSTICS, "Diagnostics", true, None::<&str>)?,
        ],
    )?;

    // No Help submenu (§12 of the mandate): About already lives in the
    // application menu per macOS convention, and nothing else here has
    // "functioning product behavior" to justify a second entry point
    // (§12: "Do not add menu items without functioning product behavior").
    Menu::with_items(app, &[&app_menu, &file_menu, &view_menu])
}

/// Routes a native menu click. `"quit"` is the one case handled entirely
/// here (see module doc comment); everything else is forwarded verbatim to
/// the WebView, where `native_menu.ts` dispatches it to the same
/// controller actions the visible UI already uses — this function never
/// contains New/Open/Save/Reset-View/etc. logic itself (§9/§20/§21 of the
/// mandate).
pub fn handle_menu_event<R: Runtime>(app: &AppHandle<R>, event: MenuEvent) {
    let id = event.id().as_ref();

    if id == MENU_ID_QUIT {
        if let Some(window) = app.get_webview_window("main") {
            // WebviewWindow::close() emits WindowEvent::CloseRequested —
            // the same native event the red close button produces, not a
            // direct process termination. See the module doc comment for
            // the full evidence chain.
            let _ = window.close();
        }
        return;
    }

    let checked = checked_state_for(app, id);
    let _ = app.emit(MENU_ACTION_EVENT, MenuActionPayload { id, checked });
}

/// Reads a just-clicked check item's own (already-toggled-by-the-OS)
/// state, for the three visibility items — `None` for every other id.
fn checked_state_for<R: Runtime>(app: &AppHandle<R>, id: &str) -> Option<bool> {
    if ![MENU_ID_VIEW_BODY, MENU_ID_VIEW_ROD, MENU_ID_VIEW_STRINGS].contains(&id) {
        return None;
    }
    find_view_check_item(app, id).and_then(|item| item.is_checked().ok())
}

fn find_view_check_item<R: Runtime>(app: &AppHandle<R>, id: &str) -> Option<CheckMenuItem<R>> {
    let menu = app.menu()?;
    let view_submenu = menu.get("view")?.as_submenu()?.clone();
    view_submenu.get(id)?.as_check_menuitem().cloned()
}

/// Build 025 M4 — the frontend's half of bidirectional Show Body/Rod/
/// Strings sync (§15/§16/§29 of the mandate): called whenever the
/// *visible* checkbox changes, so the native menu's own checked glyph
/// reflects it too. The reverse direction (native menu click -> visible
/// checkbox) needs no command — `handle_menu_event` above already reads
/// the native item's post-click state and forwards it to the frontend.
/// Requires no new WebView capability: this is an app-owned command (like
/// every `engine_*`/`select_*` command already registered), not a plugin
/// command, so it is not ACL-gated (see `capabilities/main-capability.json`,
/// which names none of those commands either) — confirmed against
/// `desktop-schema.json`, which only gates `plugin:*`-namespaced commands.
/// Generic core, kept separate from the `#[tauri::command]` wrapper below
/// (which — matching every other command in this file's siblings, e.g.
/// `commands.rs`'s `engine_*` commands against `EngineState` — is fixed to
/// the concrete `AppHandle<Wry>` production commands use throughout this
/// crate) purely so `tests/native_menu.rs` can exercise the real logic
/// against `MockRuntime` directly, the same reason `commands.rs`'s
/// `ipc_argument_binding` tests dispatch a same-shape "twin" rather than
/// the literal production command.
pub fn set_view_menu_checked_impl<R: Runtime>(
    app: &AppHandle<R>,
    layer: &str,
    checked: bool,
) -> Result<(), String> {
    let id = match layer {
        "body" => MENU_ID_VIEW_BODY,
        "rod" => MENU_ID_VIEW_ROD,
        "strings" => MENU_ID_VIEW_STRINGS,
        other => return Err(format!("unknown view layer: {other}")),
    };
    let item = find_view_check_item(app, id).ok_or_else(|| "view menu item not found".to_string())?;
    item.set_checked(checked).map_err(|e| e.to_string())
}

/// Build 025 M4 — the frontend's half of bidirectional Show Body/Rod/
/// Strings sync (§15/§16/§29 of the mandate): called whenever the
/// *visible* checkbox changes, so the native menu's own checked glyph
/// reflects it too. The reverse direction (native menu click -> visible
/// checkbox) needs no command — `handle_menu_event` above already reads
/// the native item's post-click state and forwards it to the frontend.
/// Requires no new WebView capability: this is an app-owned command (like
/// every `engine_*`/`select_*` command already registered), not a plugin
/// command, so it is not ACL-gated (see `capabilities/main-capability.json`,
/// which names none of those commands either) — confirmed against
/// `desktop-schema.json`, which only gates `plugin:*`-namespaced commands.
#[tauri::command]
pub fn set_view_menu_checked(app: AppHandle<tauri::Wry>, layer: String, checked: bool) -> Result<(), String> {
    set_view_menu_checked_impl(&app, &layer, checked)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn checked_state_for_non_check_ids_is_none() {
        // A pure/structural check that doesn't need a real app: no ID
        // outside the three visibility items should ever request a
        // checked lookup at all (avoids ever touching the menu tree for
        // Quit/File/Reset View/Report/Diagnostics).
        for id in [
            MENU_ID_QUIT,
            MENU_ID_FILE_NEW,
            MENU_ID_FILE_OPEN,
            MENU_ID_FILE_SAVE,
            MENU_ID_FILE_SAVE_AS,
            MENU_ID_FILE_EXPORT,
            MENU_ID_VIEW_RESET,
            MENU_ID_VIEW_REPORT,
            MENU_ID_VIEW_DIAGNOSTICS,
        ] {
            assert!(
                ![MENU_ID_VIEW_BODY, MENU_ID_VIEW_ROD, MENU_ID_VIEW_STRINGS].contains(&id),
                "{id} must not be treated as a check item"
            );
        }
    }
}
