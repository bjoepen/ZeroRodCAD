import { describe, expect, it } from "vitest";

import type { ZeroRodParametersValues } from "./parameters";
import {
  defaultSaveFileName,
  initialProjectSession,
  isProjectDirty,
  shouldGuardAgainstDataLoss,
  withNewProjectBaseline,
  withSavedBaseline,
} from "./project_state";

const DEFAULTS: ZeroRodParametersValues = {
  project_name: "CBG Open G",
  body_width: 38.0,
  body_depth: 9.0,
  fretboard_height: 6.9,
  rod_diameter: 3.0,
  groove_diameter: 2.94,
  rod_center_z_offset: -0.75,
  groove_front_clearance: 0.01,
  string_gauges_inch: [0.036, 0.026, 0.017],
  string_spacing: 10.0,
  string_inlet_y: 0.0,
  string_inlet_z: 2.8,
  channel_diameter: 1.15,
  channel_overrun_at_inlet: 0.8,
  channel_rod_clearance: 0.05,
  minimum_wall: 1.2,
};

function withBodyWidth(values: ZeroRodParametersValues, bodyWidth: number): ZeroRodParametersValues {
  return { ...values, body_width: bodyWidth };
}

describe("isProjectDirty (§9 of the M1 mandate)", () => {
  it("is false for a fresh session with no baseline yet", () => {
    expect(isProjectDirty(initialProjectSession(), DEFAULTS)).toBe(false);
  });

  it("is false when accepted equals the saved baseline", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(isProjectDirty(session, DEFAULTS)).toBe(false);
  });

  it("is true when accepted differs from the saved baseline", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(isProjectDirty(session, withBodyWidth(DEFAULTS, 60))).toBe(true);
  });

  it("is exactly `accepted != last_saved_state` — a differing DRAFT alone does not matter here", () => {
    // project_state.ts never sees the draft at all; isProjectDirty only
    // ever compares against `accepted`, matching §9's explicit
    // `project_dirty = accepted_current_state != last_saved_state` (not
    // `draft != saved`) — this test documents that by construction, not by
    // simulating a draft (which lives in parameter_state.ts, a different
    // module entirely).
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(isProjectDirty(session, DEFAULTS)).toBe(false);
  });

  it("a brand-new project (New) starts clean, not dirty", () => {
    const session = withNewProjectBaseline(DEFAULTS);
    expect(isProjectDirty(session, DEFAULTS)).toBe(false);
  });

  it("a brand-new project becomes dirty once its accepted state actually changes", () => {
    const session = withNewProjectBaseline(DEFAULTS);
    expect(isProjectDirty(session, withBodyWidth(DEFAULTS, 60))).toBe(true);
  });

  it("becomes clean again immediately after a successful Save", () => {
    let session = withNewProjectBaseline(DEFAULTS);
    const edited = withBodyWidth(DEFAULTS, 60);
    expect(isProjectDirty(session, edited)).toBe(true);

    session = withSavedBaseline("/tmp/x.zerorod", edited);
    expect(isProjectDirty(session, edited)).toBe(false);
  });

  it("is false when accepted is null (nothing loaded yet)", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(isProjectDirty(session, null)).toBe(false);
  });
});

describe("shouldGuardAgainstDataLoss (§22 of the M1 mandate)", () => {
  it("is false when neither project-dirty nor an uncommitted draft exists", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(shouldGuardAgainstDataLoss(session, DEFAULTS, false)).toBe(false);
  });

  it("is true when project-dirty alone is true", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(shouldGuardAgainstDataLoss(session, withBodyWidth(DEFAULTS, 60), false)).toBe(true);
  });

  it("is true when an uncommitted draft alone exists, even though project_dirty is false", () => {
    // The §22 scenario verbatim: saved=38, draft="abc" (invalid), accepted
    // still 38, project_dirty is false — but the guard must still fire.
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(shouldGuardAgainstDataLoss(session, DEFAULTS, true)).toBe(true);
  });

  it("is true when both are true", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(shouldGuardAgainstDataLoss(session, withBodyWidth(DEFAULTS, 60), true)).toBe(true);
  });
});

describe("withSavedBaseline / withNewProjectBaseline", () => {
  it("withSavedBaseline sets both the current path and the baseline", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(session.currentPath).toBe("/tmp/x.zerorod");
    expect(session.savedBaseline).toEqual(DEFAULTS);
  });

  it("withSavedBaseline deep-copies string_gauges_inch (no shared array reference)", () => {
    const session = withSavedBaseline("/tmp/x.zerorod", DEFAULTS);
    expect(session.savedBaseline?.string_gauges_inch).toEqual(DEFAULTS.string_gauges_inch);
    expect(session.savedBaseline?.string_gauges_inch).not.toBe(DEFAULTS.string_gauges_inch);
  });

  it("withNewProjectBaseline clears the current path but keeps a baseline", () => {
    const session = withNewProjectBaseline(DEFAULTS);
    expect(session.currentPath).toBeNull();
    expect(session.savedBaseline).toEqual(DEFAULTS);
  });
});

describe("defaultSaveFileName", () => {
  it("derives '<project_name>.zerorod', mirroring legacy's convention", () => {
    expect(defaultSaveFileName("CBG Open G")).toBe("CBG Open G.zerorod");
  });

  it("falls back to a fixed name when project_name is blank", () => {
    expect(defaultSaveFileName("")).toBe("project.zerorod");
    expect(defaultSaveFileName("   ")).toBe("project.zerorod");
  });
});
