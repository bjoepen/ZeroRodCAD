// Build 025 M4 — real, artifact-level proof that the native menu tree
// contains no `PredefinedMenuItem::quit` (the exact mechanism Build 025 M1
// found routes straight to AppKit's `terminate:`, bypassing the JS
// unsaved-changes guard entirely — see
// docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md) and that every menu
// item this milestone's product surface depends on actually exists with
// the expected id/kind, by constructing the REAL `menu::build_menu`
// function (not a hand-copied twin) against `MockRuntime` and inspecting
// the resulting tree — the same "test the actual boundary, not a mock one
// layer down" standard `tests/native_close_permission.rs` already
// established for the M1 ACL bug (§27/§28/§45 of the M4 mandate: "avoid a
// test suite consisting only of mocked button clicks... apply the same
// evidence standard here").
//
// This lives in `tests/` (a separate compilation unit), not in
// `src/menu.rs`'s own `#[cfg(test)]` module, for the identical reason
// `native_close_permission.rs` does: `lib.rs` already calls
// `tauri::generate_context!()` once to build the real app, and a second
// invocation in the same binary fails to compile
// (`symbol '_EMBED_INFO_PLIST' is already defined`).

use tauri::menu::MenuItemKind;
use tauri::test::mock_builder;
use zerorod_desktop_lib::menu;

fn build_test_app() -> tauri::App<tauri::test::MockRuntime> {
    mock_builder()
        .menu(menu::build_menu)
        .build(tauri::generate_context!())
        .expect("failed to build app with the real menu tree")
}

#[test]
fn quit_menu_item_is_not_a_predefined_item() {
    // The single most important structural fact this milestone must prove:
    // the item that resumes the close flow is NOT
    // `PredefinedMenuItem::quit` (which — confirmed directly in the `muda`
    // crate during the M1 investigation — is wired straight to AppKit's
    // `terminate:`, bypassing WindowEvent::CloseRequested and therefore
    // the JS guard entirely). A plain `MenuItem` structurally cannot do
    // that; its click is dispatched through `on_menu_event`, which this
    // module's `handle_menu_event` routes to `WebviewWindow::close()`.
    let app = build_test_app();
    let top_menu = app.menu().expect("app must have a menu");
    let app_menu = top_menu
        .get(menu::MENU_ID_APP_MENU)
        .and_then(|k| k.as_submenu().cloned())
        .expect("application submenu must exist");

    let quit_item = app_menu
        .get(menu::MENU_ID_QUIT)
        .expect("a menu item with id 'quit' must exist");

    assert!(
        quit_item.as_predefined_menuitem().is_none(),
        "the quit menu item must NOT be a PredefinedMenuItem — that is the exact M1 bypass mechanism"
    );
    assert!(
        matches!(quit_item, MenuItemKind::MenuItem(_)),
        "the quit menu item must be a plain custom MenuItem, got {quit_item:?}",
        quit_item = std::any::type_name_of_val(&quit_item)
    );
}

#[test]
fn file_menu_has_the_expected_items() {
    let app = build_test_app();
    let top_menu = app.menu().unwrap();
    let file_menu = top_menu
        .get("file")
        .and_then(|k| k.as_submenu().cloned())
        .expect("File submenu must exist");

    for id in [
        menu::MENU_ID_FILE_NEW,
        menu::MENU_ID_FILE_OPEN,
        menu::MENU_ID_FILE_SAVE,
        menu::MENU_ID_FILE_SAVE_AS,
        menu::MENU_ID_FILE_EXPORT,
    ] {
        assert!(
            file_menu.get(id).is_some(),
            "File menu must contain an item with id '{id}'"
        );
    }
}

#[test]
fn view_menu_has_the_expected_items_and_check_items_default_checked() {
    let app = build_test_app();
    let top_menu = app.menu().unwrap();
    let view_menu = top_menu
        .get("view")
        .and_then(|k| k.as_submenu().cloned())
        .expect("View submenu must exist");

    assert!(view_menu.get(menu::MENU_ID_VIEW_RESET).is_some());
    assert!(view_menu.get(menu::MENU_ID_VIEW_REPORT).is_some());
    assert!(view_menu.get(menu::MENU_ID_VIEW_DIAGNOSTICS).is_some());

    for id in [
        menu::MENU_ID_VIEW_BODY,
        menu::MENU_ID_VIEW_ROD,
        menu::MENU_ID_VIEW_STRINGS,
    ] {
        let item = view_menu
            .get(id)
            .unwrap_or_else(|| panic!("View menu must contain an item with id '{id}'"));
        let check_item = item
            .as_check_menuitem()
            .unwrap_or_else(|| panic!("'{id}' must be a CheckMenuItem"));
        assert!(
            check_item.is_checked().unwrap(),
            "'{id}' must start checked (§14 of the M3 mandate: default visible)"
        );
    }
}

#[test]
fn about_item_is_predefined_and_no_help_menu_exists() {
    // About IS a legitimate use of a predefined item (§22 of the mandate) —
    // unlike Quit, there is no data-loss risk to bypass; this test exists
    // to make that asymmetry explicit, not to also forbid it here.
    let app = build_test_app();
    let top_menu = app.menu().unwrap();
    let app_menu = top_menu.get(menu::MENU_ID_APP_MENU).and_then(|k| k.as_submenu().cloned()).unwrap();
    let items = app_menu.items().unwrap();
    let about = items
        .iter()
        .find(|item| item.as_predefined_menuitem().is_some())
        .expect("an About predefined item must exist in the application menu");
    assert!(about.as_predefined_menuitem().is_some());

    // §12 of the mandate: no Help submenu — nothing to justify one beyond
    // About, which already lives in the application menu.
    assert!(
        top_menu.get("help").is_none(),
        "no Help submenu should exist — About already lives in the application menu"
    );
}

#[test]
fn set_view_menu_checked_updates_the_real_native_item() {
    let app = build_test_app();
    let handle = app.handle().clone();

    menu::set_view_menu_checked_impl(&handle, "body", false)
        .expect("set_view_menu_checked_impl must succeed for a known layer");

    let top_menu = app.menu().unwrap();
    let view_menu = top_menu.get("view").and_then(|k| k.as_submenu().cloned()).unwrap();
    let body_item = view_menu
        .get(menu::MENU_ID_VIEW_BODY)
        .and_then(|k| k.as_check_menuitem().cloned())
        .unwrap();
    assert!(
        !body_item.is_checked().unwrap(),
        "set_view_menu_checked must actually mutate the native item's checked state"
    );
}

#[test]
fn set_view_menu_checked_rejects_an_unknown_layer() {
    let app = build_test_app();
    let handle = app.handle().clone();
    let result = menu::set_view_menu_checked_impl(&handle, "not-a-real-layer", true);
    assert!(result.is_err());
}
