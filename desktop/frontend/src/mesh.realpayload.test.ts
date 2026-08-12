// Feeds a REAL zerorod-mesh/v1 payload — produced by the actual bundled
// sidecar binary Rust would spawn, not a synthetic fixture — through the
// real meshContractToGeometries() conversion path. This is the same bar
// TE-002's own Preview-Validation.md set: "build correct THREE.BufferGeometry
// from the real ZeroRod payload (not synthetic data)". Skipped if the
// productive onedir sidecar hasn't been built (see
// docs/migration/BUILD-022-M2-SIDECAR-LIFECYCLE.md "Reproducing the build").

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { meshContractToGeometries } from "./mesh";

const SIDECAR_BINARY = resolve(
  __dirname,
  "../../sidecar-dist/zerorod-engine/zerorod-engine",
);

function fetchRealPreviewPayload(): unknown {
  const input =
    JSON.stringify({
      schema: "zerorod-sidecar/v1",
      request_id: "real-payload-test",
      command: "preview",
      parameters: {},
    }) +
    "\n" +
    JSON.stringify({
      schema: "zerorod-sidecar/v1",
      request_id: "shutdown",
      command: "shutdown",
      parameters: {},
    }) +
    "\n";

  const output = execFileSync(SIDECAR_BINARY, ["--persistent"], {
    input,
    encoding: "utf-8",
    timeout: 30_000,
  });
  const lines = output.split("\n").filter((line) => line.trim().length > 0);
  const previewResponse = JSON.parse(lines[0]);
  if (!previewResponse.ok) {
    throw new Error(`sidecar returned an error: ${JSON.stringify(previewResponse.error)}`);
  }
  return previewResponse.result;
}

describe.skipIf(!existsSync(SIDECAR_BINARY))("meshContractToGeometries (real bundled binary payload)", () => {
  it("converts the real ZeroRod payload into renderable body/rod meshes and string lines", () => {
    const payload = fetchRealPreviewPayload();
    const { meshes, lines, bounds } = meshContractToGeometries(payload);

    const names = meshes.map((m) => m.name).sort();
    expect(names).toEqual(["body", "rod"]);
    expect(lines.length).toBeGreaterThan(0);

    for (const mesh of meshes) {
      expect(mesh.geometry.attributes.position.count).toBeGreaterThan(0);
      expect(mesh.geometry.index!.count).toBeGreaterThan(0);
      expect(mesh.geometry.attributes.normal).toBeDefined();
    }

    expect(bounds.min.length).toBe(3);
    expect(bounds.max.length).toBe(3);
  });
});
