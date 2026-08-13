// Build 025 M3 — the compact model-view tool area (§25 of the mandate):
// Reset View plus Body/Rod/Strings visibility, parity with legacy's
// `preview_widget.py`/`main_window.py` controls (`reset_view()`,
// `show_body`/`show_rod`/`show_strings`). Deliberately NOT placed in
// Diagnostics (§26 — this is normal product functionality, not technical
// information) and deliberately a plain product-labeled control strip, not
// a debug panel (§15 — no Three.js/group terminology in the UI).
//
// Every action here is presentation-only, wired straight to
// `preview.ts`'s `resetView`/`setLayerVisible`/`isLayerVisible` — no
// backend call, no geometry change, no project-dirty effect (§9/§10),
// which this module enforces simply by never being given any IO capable of
// doing those things in the first place (mirrors project_panel.ts's/
// export_panel.ts's isolation discipline: this module only talks to the
// rest of the app through the small `ViewControlsIO` interface below).

import type { ModelLayer } from "./preview";

export interface ViewControlsIO {
  resetView: () => void;
  setLayerVisible: (layer: ModelLayer, visible: boolean) => void;
  isLayerVisible: (layer: ModelLayer) => boolean;
}

export interface ViewControlsController {
  dispose: () => void;
}

const LAYER_LABELS: Record<ModelLayer, string> = {
  body: "Body",
  rod: "Rod",
  strings: "Strings",
};

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function createViewControlsController(
  container: HTMLElement,
  io: ViewControlsIO,
): ViewControlsController {
  const layers: ModelLayer[] = ["body", "rod", "strings"];

  const checkboxesHtml = layers
    .map((layer) => {
      const id = `view-layer-${layer}`;
      const checked = io.isLayerVisible(layer) ? " checked" : "";
      return `
        <label class="view-controls-layer" for="${id}">
          <input type="checkbox" id="${id}" data-layer="${layer}"${checked} />
          ${escapeHtml(LAYER_LABELS[layer])}
        </label>
      `;
    })
    .join("");

  container.innerHTML = `
    <div class="view-controls" role="group" aria-label="Model view">
      ${checkboxesHtml}
      <button type="button" class="view-controls-reset" data-action="reset-view">Reset View</button>
    </div>
  `;

  for (const layer of layers) {
    container
      .querySelector<HTMLInputElement>(`#view-layer-${layer}`)
      ?.addEventListener("change", (event) => {
        io.setLayerVisible(layer, (event.target as HTMLInputElement).checked);
      });
  }
  container.querySelector('[data-action="reset-view"]')?.addEventListener("click", () => {
    io.resetView();
  });

  function dispose(): void {
    // No timers/subscriptions to release — kept for interface symmetry
    // with the other panel controllers.
  }

  return { dispose };
}
