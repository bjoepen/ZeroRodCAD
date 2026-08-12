import { describe, expect, it } from "vitest";
import * as THREE from "three";
import {
  formatErrorDetail,
  formatReadyDetail,
  previewStateToStatusValue,
  summarizeRenderResult,
  type PreviewState,
} from "./preview";
import type { RenderableMesh } from "./mesh";

// createPreviewController itself is not unit-tested here: it constructs a
// real THREE.WebGLRenderer, which has no GPU context under jsdom/vitest.
// Per the mandate's own guidance ("avoid fragile browser/GPU automation
// where pure logic tests suffice"), the state machine and formatting logic
// it depends on are extracted into the pure functions tested below instead;
// the renderer itself is covered by the real app build/screenshot
// validation and the human validation checklist.

describe("previewStateToStatusValue", () => {
  const cases: [PreviewState, string][] = [
    ["idle", "NOT_READY"],
    ["loading", "RUNNING"],
    ["ready", "READY"],
    ["error", "ERROR"],
  ];

  it.each(cases)("maps %s to %s", (state, expected) => {
    expect(previewStateToStatusValue(state)).toBe(expected);
  });
});

function renderableMesh(vertexCount: number, triangleCount: number): RenderableMesh {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(vertexCount * 3), 3),
  );
  geometry.setIndex(new THREE.BufferAttribute(new Uint16Array(triangleCount * 3), 1));
  return { name: "test", geometry };
}

describe("summarizeRenderResult", () => {
  it("sums vertices and triangles across multiple meshes", () => {
    const meshes = [renderableMesh(720, 710), renderableMesh(146, 140)];
    const summary = summarizeRenderResult(meshes, []);
    expect(summary.vertexCount).toBe(866);
    expect(summary.triangleCount).toBe(850);
    expect(summary.lineCount).toBe(0);
  });

  it("counts lines separately from meshes", () => {
    const lines: RenderableMesh[] = [
      { name: "strings", geometry: new THREE.BufferGeometry() },
    ];
    const summary = summarizeRenderResult([], lines);
    expect(summary.lineCount).toBe(1);
  });

  it("handles an empty mesh/line set without throwing", () => {
    expect(() => summarizeRenderResult([], [])).not.toThrow();
    expect(summarizeRenderResult([], [])).toEqual({
      vertexCount: 0,
      triangleCount: 0,
      lineCount: 0,
    });
  });
});

describe("formatReadyDetail", () => {
  it("includes vertex, triangle, line counts and both timings", () => {
    const text = formatReadyDetail({ vertexCount: 866, triangleCount: 850, lineCount: 1 }, 123, 4.5);
    expect(text).toContain("866 vertices");
    expect(text).toContain("850 triangles");
    expect(text).toContain("1 line(s)");
    expect(text).toContain("123ms");
    expect(text).toContain("4.5ms");
  });
});

describe("formatErrorDetail", () => {
  it("formats a structured EngineError as code: message", () => {
    expect(formatErrorDetail({ code: "timeout", message: "no response" })).toBe(
      "timeout: no response",
    );
  });

  it("formats a native Error by its message", () => {
    expect(formatErrorDetail(new Error("invalid mesh payload: bad data"))).toBe(
      "invalid mesh payload: bad data",
    );
  });

  it("falls back to String() for anything else", () => {
    expect(formatErrorDetail("plain string failure")).toBe("plain string failure");
  });
});
