// Build 025 M1 — project session state. Owns:
//   - the project session model (§8 of the mandate): current project path,
//     the saved baseline (the parameter values as of the last successful
//     Save/Open), and project-dirty derived from the two
//   - the "uncommitted draft" concept (§22 of the mandate), kept explicitly
//     separate from project-dirty rather than redefining it
//   - the default Save As filename derivation
//
// Deliberately does not duplicate Build 023 M4's draft/accepted state
// machine (parameter_state.ts / parameter_panel.ts) — this module only adds
// the one new concept Build 025 M1 actually needs on top of it: "has
// `accepted` changed since the project was last saved/opened." Every
// function here is pure (old state in, new state out), mirroring
// parameter_state.ts's own style.

import { valuesEqual } from "./parameter_state";
import type { ZeroRodParametersValues } from "./parameters";

export interface ProjectSessionState {
  /** Absolute path of the file this project was last saved to or opened
   * from — `null` for a brand-new, never-saved project (§10/§14 of the
   * mandate: New clears this). */
  currentPath: string | null;
  /** The parameter values as of the last successful Save or Open — the
   * baseline `project_dirty` compares `accepted` against. `null` only
   * before the very first project state exists (never reached in practice
   * once the app has loaded canonical defaults as an implicit "New"). */
  savedBaseline: ZeroRodParametersValues | null;
}

export function initialProjectSession(): ProjectSessionState {
  return { currentPath: null, savedBaseline: null };
}

/** §9 of the mandate, verbatim: `project_dirty = accepted_current_state !=
 * last_saved_state` — deliberately NOT `draft != saved` (a merely-typed,
 * not-yet-accepted edit does not by itself make the project dirty). A
 * brand-new project (`savedBaseline` set to the canonical defaults at New
 * time, per project_panel.ts) therefore starts clean and only becomes dirty
 * once the user's edits are actually accepted into the preview. */
export function isProjectDirty(
  session: ProjectSessionState,
  accepted: ZeroRodParametersValues | null,
): boolean {
  if (session.savedBaseline === null || accepted === null) return false;
  return !valuesEqual(session.savedBaseline, accepted);
}

/** §22 of the mandate: a genuinely different condition from `project_dirty`
 * — "the user has typed something not yet reflected in `accepted`," valid
 * or not (mirrors `isDraftDirty`'s own "including an invalid in-progress
 * edit" semantics, exposed by parameter_panel.ts's `hasUncommittedDraft`).
 * The two are combined with a boolean OR at the call site (project_panel.ts)
 * to decide whether the unsaved-changes guard should fire — never merged
 * into a single redefined `project_dirty`, per the mandate's explicit
 * instruction not to do so. */
export function shouldGuardAgainstDataLoss(
  session: ProjectSessionState,
  accepted: ZeroRodParametersValues | null,
  hasUncommittedDraft: boolean,
): boolean {
  return isProjectDirty(session, accepted) || hasUncommittedDraft;
}

/** Records a successful Save or Open as the new baseline — `path` becomes
 * the current project path, `values` becomes the saved baseline, so
 * `project_dirty` is `false` immediately afterward (until the next accepted
 * change). Shared by Save, Save As, and Open — all three end in the same
 * "this is now the on-disk truth" state. */
export function withSavedBaseline(
  path: string,
  values: ZeroRodParametersValues,
): ProjectSessionState {
  return { currentPath: path, savedBaseline: { ...values, string_gauges_inch: [...values.string_gauges_inch] } };
}

/** New Project's session reset (§10): no current path, but a baseline is
 * still recorded (the canonical defaults just loaded) — not `null` — so a
 * freshly-created project reads as clean until actually edited, not as
 * permanently dirty for lack of a comparison baseline. */
export function withNewProjectBaseline(defaults: ZeroRodParametersValues): ProjectSessionState {
  return {
    currentPath: null,
    savedBaseline: { ...defaults, string_gauges_inch: [...defaults.string_gauges_inch] },
  };
}

/** Legacy's own Save As default filename convention
 * (`main_window.py:466-483`: `f"{project_name}.zerorod"`), carried forward
 * per the Project Persistence Analysis's explicit "no evidence against it"
 * finding. Falls back to a fixed name if `projectName` is blank (mirrors
 * `zerorodcad.export._safe_name`'s "zerorod" fallback in spirit, though this
 * is a display default, not the sanitized on-disk name project.py itself
 * produces no fallback for). */
export function defaultSaveFileName(projectName: string): string {
  const trimmed = projectName.trim();
  return `${trimmed === "" ? "project" : trimmed}.zerorod`;
}
