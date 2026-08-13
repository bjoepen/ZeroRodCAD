import { getCurrentWindow } from "@tauri-apps/api/window";
import "./style.css";
import { fetchAppInfo } from "./app_info";
import { createDiagnosticsPanelController } from "./diagnostics_panel";
import { fetchEngineStatus, fetchSidecarStatus } from "./engine";
import { createExportPanelController } from "./export_panel";
import { createParameterPanelController } from "./parameter_panel";
import { createPreviewController, type PreviewState } from "./preview";
import { createProjectPanelController } from "./project_panel";
import { createStartupController } from "./startup";

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
// model) is superseded by the automatic initial preview this build adds
// (parameter_panel.ts's `load()`, coordinated by startup.ts) — per the
// mandate's own scope freeze (§2), a manual Reset/Fit View replacement is
// explicitly Build 025 M3's job, not built here.
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
      <section class="viewport" id="viewport"></section>
    </div>
  </main>
`;

const startupPanelEl = document.querySelector<HTMLDivElement>("#startup-panel")!;
const viewportEl = document.querySelector<HTMLDivElement>("#viewport")!;
const parameterPanelEl = document.querySelector<HTMLDivElement>("#parameter-panel")!;
const exportPanelEl = document.querySelector<HTMLDivElement>("#export-panel")!;
const projectPanelEl = document.querySelector<HTMLDivElement>("#project-panel")!;
const diagnosticsPanelEl = document.querySelector<HTMLDivElement>("#diagnostics-panel")!;

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
const parameterPanel = createParameterPanelController(
  parameterPanelEl,
  {
    fetchPreview: preview.fetchPreview,
    commitPreview: preview.commitPreview,
  },
  () => {
    exportPanelRef?.refreshEnablement();
    projectPanelRef?.refreshEnablement();
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

const diagnosticsPanel = createDiagnosticsPanelController(diagnosticsPanelEl, {
  fetchAppInfo,
  fetchEngineStatus,
  fetchSidecarStatus,
});

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
// docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md. Known limitation,
// unchanged by M2 (§3/§32 of the M2 mandate, reserved for Build 025 M4):
// the implicit default macOS Quit/⌘Q menu item bypasses this guard
// entirely — see docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md and
// docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md.
void getCurrentWindow().onCloseRequested(async (event) => {
  const proceed = await projectPanel.confirmQuit();
  if (!proceed) {
    event.preventDefault();
  }
});

// Build 025 M2 (§7/§10 of the mandate): normal startup performs exactly one
// initialization sequence — no manual "Start Engine"/"Load Preview" step,
// no competing parallel calls. `startup.start()` is the one entry point;
// it awaits `parameterPanel.load()` end to end (defaults, lazy sidecar
// spawn, automatic initial preview) exactly once.
void startup.start();
