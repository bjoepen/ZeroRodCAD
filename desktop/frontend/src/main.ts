import { getCurrentWindow } from "@tauri-apps/api/window";
import "./style.css";
import { fetchAppInfo } from "./app_info";
import { createCloseRequestHandler } from "./close_flow";
import { createDiagnosticsPanelController } from "./diagnostics_panel";
import { fetchEngineStatus, fetchSidecarStatus } from "./engine";
import { createExportPanelController } from "./export_panel";
import { createNativeMenuBridge } from "./native_menu";
import { createParameterPanelController } from "./parameter_panel";
import { createPreviewController, type PreviewState } from "./preview";
import { createProjectPanelController } from "./project_panel";
import { createReportPanelController } from "./report_panel";
import { createStartupController } from "./startup";
import { createViewControlsController } from "./view_controls";

const appEl = document.querySelector<HTMLDivElement>("#app")!;

// The DOM shell is built exactly once (below, in this module's top level).
// Only specific sub-panels re-render afterward — never the whole #app
// innerHTML — because the viewport div holds a live Three.js canvas that a
// full re-render would tear down and silently orphan on every status
// change.
//
// Build 025 M2 (§14/§15 of the mandate — "the product UI must not be a
// debug console"): this shell used to also carry a 5-row technical status
// panel and four development buttons (Start/Check Engine, Ping Engine,
// Request Preview Data, Load/Refresh ZeroRod) plus a raw "last action" log
// — see docs/migration/BUILD-025-LIFECYCLE-ANALYSIS.md §2/§3 for the full
// per-control classification this removal follows. Their genuine
// diagnostic value (pid, ping latency, sidecar/CadQuery/OCP version info,
// build identity) is not deleted — it now lives in the Diagnostics panel
// (diagnostics_panel.ts), reachable but outside the normal product flow.
// "Load/Refresh ZeroRod"'s actual capability (fetch + render the current
// model) is superseded by the automatic initial preview added in M2
// (parameter_panel.ts's `load()`, coordinated by startup.ts).
//
// Build 025 M3 (§25 of the mandate) adds one compact model-view tool area
// — Reset View plus Body/Rod/Strings visibility (view_controls.ts) and the
// Instrument Report (report_panel.ts) — subordinate to the viewport, not a
// redesign: both sit in a new `.viewport-column` above the (unmoved)
// viewport, the sidebar/parameters-column are untouched, and neither lives
// in Diagnostics (§26 — this is normal product functionality, not
// technical information).
appEl.innerHTML = `
  <main class="foundation">
    <h1>ZeroRodCAD Desktop 2.0</h1>
    <div id="startup-panel"></div>
    <div class="layout">
      <section class="sidebar">
        <section class="project-panel-container" id="project-panel"></section>
        <section class="export-panel-container" id="export-panel"></section>
        <section class="diagnostics-container" id="diagnostics-panel"></section>
      </section>
      <div class="parameters-column">
        <section class="parameters" id="parameter-panel"></section>
      </div>
      <div class="viewport-column">
        <section class="view-controls-container" id="view-controls"></section>
        <section class="report-panel-container" id="report-panel"></section>
        <section class="viewport" id="viewport"></section>
      </div>
    </div>
  </main>
`;

const startupPanelEl = document.querySelector<HTMLDivElement>("#startup-panel")!;
const viewportEl = document.querySelector<HTMLDivElement>("#viewport")!;
const parameterPanelEl = document.querySelector<HTMLDivElement>("#parameter-panel")!;
const exportPanelEl = document.querySelector<HTMLDivElement>("#export-panel")!;
const projectPanelEl = document.querySelector<HTMLDivElement>("#project-panel")!;
const diagnosticsPanelEl = document.querySelector<HTMLDivElement>("#diagnostics-panel")!;
const viewControlsEl = document.querySelector<HTMLDivElement>("#view-controls")!;
const reportPanelEl = document.querySelector<HTMLDivElement>("#report-panel")!;

function handlePreviewStateChange(_state: PreviewState, _detail: string): void {
  // Build 025 M2: the old status panel's "3D preview" row (and the
  // "Load / Refresh ZeroRod" button's own detail text) that used to consume
  // this callback are gone (§14/§15 of the mandate) — preview state is now
  // communicated to the user through the parameter panel's existing
  // always-visible live-status line instead (parameter_panel.ts's
  // `setLiveStatus`, already wired through the automatic-initial-preview
  // path added there). `createPreviewController` still requires a
  // listener, so this stays a real, named, intentionally-empty function
  // rather than being deleted along with its call site.
}

const preview = createPreviewController(viewportEl, handlePreviewStateChange);
// Build 023 M4: the panel's live-preview scheduler and its Apply fallback
// both drive the same fetch/commit pair the automatic initial preview
// (parameter_panel.ts's `load()`, Build 025 M2) is itself built from — one
// pipeline, per the M4 mandate — but they need the fetch and commit steps
// separately so a stale (superseded) result can be discarded before it ever
// reaches the scene (see live_preview.ts and parameter_panel.ts's module
// doc comments). Build 024 M2: the export panel needs to react whenever
// `accepted` or the live-preview status might have changed (its trigger's
// enablement depends on both), but is created after `parameterPanel` while
// `parameterPanel` itself needs the notify callback at construction time —
// this forward reference (assigned synchronously, right below, before any
// async work can run) breaks that ordering cycle without either module
// importing the other's internals. Build 025 M1 extends the same
// forward-reference pattern to the project panel (its dirty
// indicator/Save enablement depend on the same `accepted`/live-preview-
// status changes).
let exportPanelRef: { refreshEnablement: () => void } | null = null;
let projectPanelRef: { refreshEnablement: () => void } | null = null;
let reportPanelRef: { refreshIfVisible: () => void } | null = null;
const parameterPanel = createParameterPanelController(
  parameterPanelEl,
  {
    fetchPreview: preview.fetchPreview,
    commitPreview: preview.commitPreview,
  },
  () => {
    exportPanelRef?.refreshEnablement();
    projectPanelRef?.refreshEnablement();
    // Build 025 M3 (§21 of the mandate): the report follows accepted-state
    // transitions, not raw draft typing — refreshIfVisible() itself is a
    // no-op unless the panel is open AND accepted actually changed, so
    // this frequent callback (fired on every live-preview status
    // transition, not just successful ones) never causes duplicate
    // requests on every keystroke.
    reportPanelRef?.refreshIfVisible();
  },
);
const exportPanel = createExportPanelController(exportPanelEl, {
  getAcceptedRequest: () => parameterPanel.getAcceptedRequest(),
  getLivePreviewStatus: () => parameterPanel.getLivePreviewStatus(),
});
exportPanelRef = exportPanel;
const projectPanel = createProjectPanelController(projectPanelEl, {
  getAccepted: () => parameterPanel.getAccepted(),
  hasUncommittedDraft: () => parameterPanel.hasUncommittedDraft(),
  getLivePreviewStatus: () => parameterPanel.getLivePreviewStatus(),
  loadProjectValues: (values) => parameterPanel.loadProjectValues(values),
});
projectPanelRef = projectPanel;

const reportPanel = createReportPanelController(reportPanelEl, {
  getAccepted: () => parameterPanel.getAccepted(),
});
reportPanelRef = reportPanel;

// Build 025 M4 (§15/§16/§29 of the mandate): the visible checkbox and the
// native View menu's checked state must never drift apart. Both directions
// funnel through `nativeMenu.setLayerVisible` (native_menu.ts) — the ONE
// place that updates the scene, the visible checkbox, AND the native
// menu's checked glyph together — so `view_controls.ts`'s own IO is wired
// to that shared function via this forward reference, not directly to
// `preview.setLayerVisible`, the same ordering-cycle pattern
// `exportPanelRef`/`projectPanelRef`/`reportPanelRef` above already use.
let nativeMenuRef: { setLayerVisible: (layer: import("./preview").ModelLayer, visible: boolean) => void } | null =
  null;
const viewControls = createViewControlsController(viewControlsEl, {
  resetView: () => preview.resetView(),
  setLayerVisible: (layer, visible) => nativeMenuRef?.setLayerVisible(layer, visible),
  isLayerVisible: (layer) => preview.isLayerVisible(layer),
});

const diagnosticsPanel = createDiagnosticsPanelController(diagnosticsPanelEl, {
  fetchAppInfo,
  fetchEngineStatus,
  fetchSidecarStatus,
});

// Build 025 M4 (§9/§20/§21 of the mandate): the native menu bridge is the
// one place a "menu-action" event from Rust turns into a call on the exact
// same controller methods the visible UI already uses — see
// native_menu.ts's own module doc comment. "quit" never reaches this
// bridge at all (handled entirely natively — see main.ts's
// `onCloseRequested` comment above and menu.rs's own doc comment).
const nativeMenu = createNativeMenuBridge({
  preview: {
    resetView: () => preview.resetView(),
    setLayerVisible: (layer, visible) => preview.setLayerVisible(layer, visible),
  },
  viewControls,
  projectPanel,
  exportPanel,
  reportPanel,
  diagnosticsPanel,
});
nativeMenuRef = nativeMenu;

// Build 025 M2 (§54 of the mandate): the startup sequence's *presentation*
// (delayed "Preparing…" text, friendly Retry/Show-Details failure surface)
// is owned entirely by startup.ts, not stacked into this file — main.ts's
// only job is wiring `io.run` to the one real startup action,
// `parameterPanel.load()` (which itself performs the canonical-defaults
// fetch and the automatic initial preview, through the existing M3/M4
// pipeline — see parameter_panel.ts's module doc comment).
const startup = createStartupController(startupPanelEl, {
  run: () => parameterPanel.load(),
});

window.addEventListener("beforeunload", () => {
  preview.dispose();
  parameterPanel.dispose();
  exportPanel.dispose();
  projectPanel.dispose();
  diagnosticsPanel.dispose();
  reportPanel.dispose();
  viewControls.dispose();
  nativeMenu.dispose();
  startup.dispose();
});

// Build 025 M1 (§19/§20 of the mandate): ZeroRodCAD has exactly one window
// and no menu bar yet (native menus are Build 025 M4's job) — closing that
// window IS quitting the app for this build, so this is the single,
// documented interception point for the unsaved-changes guard, not assumed
// equivalent by accident. Tauri awaits this async handler before deciding
// whether the close proceeds (the documented onCloseRequested pattern:
// `event.preventDefault()` is called ONLY to cancel — omitting it lets the
// close continue normally), so a resolved "proceed" needs no explicit close
// call here at all; it simply falls through into Tauri's own close, which
// continues into the existing, unchanged `RunEvent::ExitRequested` →
// `engine::kill_if_running` path (lib.rs) — Build 022's shutdown logic is
// neither duplicated nor bypassed. Build 025 M1 corrective fix: this relies
// on `core:window:allow-destroy` (capabilities/main-capability.json) — see
// docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md.
//
// Build 025 M4 (§7/§8/§9 of the mandate — "ONE unsaved-changes decision
// model"): the native "Quit ZeroRodCAD" menu item (and its Cmd+Q
// accelerator) is now a plain custom Rust menu item — not
// `PredefinedMenuItem::quit`, which is what used to bypass this guard by
// routing straight to AppKit's `terminate:` (the M1 finding, see
// BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md) — whose click handler
// (`desktop/src-tauri/src/menu.rs`) calls `WebviewWindow::close()`. That
// Rust method "emits WindowEvent::CloseRequested first like a
// user-initiated close request" (its own doc comment) — i.e. it produces
// the *exact same native event* the red close button does, confirmed by
// reading tauri-runtime-wry's dispatcher directly: both the red button and
// `window.close()` route through the identical `on_close_requested`
// function. So this one handler below is *already* Quit's guard too — no
// second implementation was added anywhere.
//
// Re-entrancy (§10 of the M4 mandate — repeated Cmd+Q, Cmd+Q while the red
// close guard is active, red close while a Cmd+Q guard is active): each
// native trigger calls `WebviewWindow::close()`/produces its own
// WindowEvent::CloseRequested, so two overlapping attempts would otherwise
// call `projectPanel.confirmQuit()` twice concurrently — a second
// Save/Discard/Cancel dialog stacked on the first. `close_flow.ts`'s
// `createCloseRequestHandler` makes every close attempt that arrives while
// one is still being decided simply defer to that SAME in-flight decision
// (the earlier attempt's eventual "proceed" is what actually closes the
// window, via its own event's fallthrough) rather than starting a second
// one — extracted into its own module (unlike everything else in this
// file) specifically so this safety-critical property is directly unit
// tested, not only exercised by the real app.
void getCurrentWindow().onCloseRequested(
  createCloseRequestHandler({ confirmQuit: () => projectPanel.confirmQuit() }),
);

// Build 025 M2 (§7/§10 of the mandate): normal startup performs exactly one
// initialization sequence — no manual "Start Engine"/"Load Preview" step,
// no competing parallel calls. `startup.start()` is the one entry point;
// it awaits `parameterPanel.load()` end to end (defaults, lazy sidecar
// spawn, automatic initial preview) exactly once.
void startup.start();
