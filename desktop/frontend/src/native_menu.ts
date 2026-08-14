// Build 025 M4 — the native menu bridge (§9/§20/§21 of the mandate: "the
// native menu is not a second application... it is another entrance into
// the SAME application actions"). This module's only job is translating
// native menu clicks into calls on the exact same controller methods the
// visible UI already uses — it owns no project/export/preview/report
// decision logic of its own, and it is the ONE place Show Body/Rod/Strings
// visibility gets pushed into both the preview scene and the native menu's
// own checked state, so a change from either direction (native menu click
// or the visible checkbox) can never drift out of sync with the other
// (§15/§16/§29 of the mandate).
//
// "quit" is deliberately absent from the switch below: it is handled
// entirely in Rust (`desktop/src-tauri/src/menu.rs`'s `handle_menu_event`,
// which resumes through `WebviewWindow::close()` — the same native event
// main.ts's `onCloseRequested` already guards) and is never forwarded to
// the WebView as a `"menu-action"` event at all.

import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type { DiagnosticsPanelController } from "./diagnostics_panel";
import type { ExportPanelController } from "./export_panel";
import type { ModelLayer } from "./preview";
import type { ProjectPanelController } from "./project_panel";
import type { ReportPanelController } from "./report_panel";
import type { ViewControlsController } from "./view_controls";

/** The event payload Rust's `menu::MenuActionPayload` serializes — `checked`
 * is present only for the three visibility items (§16 of the mandate: Rust
 * reports the native item's own already-toggled state, the frontend never
 * has to guess/complement a value). */
export interface MenuActionPayload {
  id: string;
  checked?: boolean;
}

export const MENU_ACTION_EVENT = "menu-action";

const MODEL_LAYER_MENU_IDS: Record<string, ModelLayer> = {
  "view-body": "body",
  "view-rod": "rod",
  "view-strings": "strings",
};

export interface NativeMenuDeps {
  preview: {
    resetView: () => void;
    setLayerVisible: (layer: ModelLayer, visible: boolean) => void;
  };
  viewControls: Pick<ViewControlsController, "setCheckboxState">;
  projectPanel: Pick<ProjectPanelController, "triggerNew" | "triggerOpen" | "triggerSave" | "triggerSaveAs">;
  exportPanel: Pick<ExportPanelController, "triggerExport">;
  reportPanel: Pick<ReportPanelController, "open">;
  diagnosticsPanel: Pick<DiagnosticsPanelController, "open">;
}

export interface NativeMenuBridge {
  /** Build 025 M4 — the ONE function that ever changes layer visibility
   * (§15 of the mandate: menu and visible control operate on the same
   * state). Called both by this module's own "menu-action" handler (a
   * native menu click) and, via `main.ts`'s wiring, by the visible
   * checkbox's own change handler — so both directions funnel through the
   * same three steps: update the scene, reflect it in the visible
   * checkbox, and sync the native menu's checked glyph. Exposed so
   * `main.ts` can wire `view_controls.ts`'s IO to it instead of directly
   * to `preview.setLayerVisible`. */
  setLayerVisible: (layer: ModelLayer, visible: boolean) => void;
  dispose: () => void;
}

/** Handles one already-decoded menu action — exported separately from the
 * event subscription so the routing logic itself (§28 of the mandate:
 * "prove native menu ID -> expected application event/action") is
 * unit-testable without needing a real Tauri event listener. */
export function dispatchMenuAction(payload: MenuActionPayload, deps: NativeMenuDeps, setLayerVisible: (layer: ModelLayer, visible: boolean) => void): void {
  const layer = MODEL_LAYER_MENU_IDS[payload.id];
  if (layer) {
    setLayerVisible(layer, payload.checked ?? true);
    return;
  }
  switch (payload.id) {
    case "file-new":
      deps.projectPanel.triggerNew();
      break;
    case "file-open":
      deps.projectPanel.triggerOpen();
      break;
    case "file-save":
      deps.projectPanel.triggerSave();
      break;
    case "file-save-as":
      deps.projectPanel.triggerSaveAs();
      break;
    case "file-export":
      deps.exportPanel.triggerExport();
      break;
    case "view-reset":
      deps.preview.resetView();
      break;
    case "view-report":
      deps.reportPanel.open();
      break;
    case "view-diagnostics":
      deps.diagnosticsPanel.open();
      break;
    default:
      // An unrecognized id must never crash the bridge — e.g. a future
      // Rust-side menu addition without a matching frontend case yet.
      break;
  }
}

export function createNativeMenuBridge(deps: NativeMenuDeps): NativeMenuBridge {
  function setLayerVisible(layer: ModelLayer, visible: boolean): void {
    deps.preview.setLayerVisible(layer, visible);
    deps.viewControls.setCheckboxState(layer, visible);
    // Best-effort: a failure here (e.g. the native item somehow missing)
    // must not block the actual visibility change, which has already
    // happened above.
    void invoke("set_view_menu_checked", { layer, checked: visible }).catch(() => {});
  }

  let unlisten: UnlistenFn | null = null;
  let disposed = false;
  void listen<MenuActionPayload>(MENU_ACTION_EVENT, (event) => {
    dispatchMenuAction(event.payload, deps, setLayerVisible);
  }).then((fn) => {
    if (disposed) {
      fn();
    } else {
      unlisten = fn;
    }
  });

  function dispose(): void {
    disposed = true;
    unlisten?.();
  }

  return { setLayerVisible, dispose };
}
