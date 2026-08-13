import { describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

import { renderReportMarkdownToHtml, requestReport } from "./report";
import { PARAMETERS_SCHEMA, type ZeroRodParametersValues } from "./parameters";

const DEFAULT_VALUES: ZeroRodParametersValues = {
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

// Captured verbatim from a real `build_report(default_parameters())` call
// (src/zerorodcad/report.py) — the exact Markdown subset this module's
// renderer must handle correctly, not a hand-simplified approximation.
const REAL_DEFAULT_REPORT_MARKDOWN = `# Instrument Report – CBG Open G

## Parameters

| Parameter | Value |
|---|---:|
| Body width | 38.00 mm |
| Body depth | 9.00 mm |
| Fretboard height | 6.90 mm |
| Rod diameter | 3.00 mm |
| Groove diameter | 2.94 mm |
| Strings | 3 |
| String spacing | 10.00 mm |
| Entry angle | 39.06° |

## Strings

| No. | Gauge | Diameter | Height over fretboard |
|---:|---:|---:|---:|
| 1 | 0.036 in | 0.914 mm | 1.207 mm |
| 2 | 0.026 in | 0.660 mm | 1.080 mm |
| 3 | 0.017 in | 0.432 mm | 0.966 mm |

## Validation

- All parameter checks passed.

## Notice

The calculated geometry must be verified by CAD inspection, slicer review and a physical prototype before use.`;

describe("requestReport", () => {
  it("invokes engine_report with the parameters.ts request shape (matching requestPreviewMeshWithParameters)", async () => {
    invokeMock.mockResolvedValueOnce({ markdown: "# Instrument Report – CBG Open G" });

    const result = await requestReport(DEFAULT_VALUES);

    expect(invokeMock).toHaveBeenCalledWith("engine_report", {
      parameters: { schema: PARAMETERS_SCHEMA, values: DEFAULT_VALUES },
    });
    expect(result.markdown).toBe("# Instrument Report – CBG Open G");
  });
});

describe("renderReportMarkdownToHtml — against the real build_report() output", () => {
  const html = renderReportMarkdownToHtml(REAL_DEFAULT_REPORT_MARKDOWN);

  it("renders the H1 title as a heading, not a raw '#'", () => {
    expect(html).toContain("<h2>Instrument Report – CBG Open G</h2>");
    expect(html).not.toContain("# Instrument Report");
  });

  it("renders each '##' section as its own heading", () => {
    expect(html).toContain("<h3>Parameters</h3>");
    expect(html).toContain("<h3>Strings</h3>");
    expect(html).toContain("<h3>Validation</h3>");
    expect(html).toContain("<h3>Notice</h3>");
  });

  it("renders the Parameters table as a real table with header and data cells", () => {
    expect(html).toContain("<table>");
    expect(html).toContain("<th>Parameter</th>");
    expect(html).toContain("<th>Value</th>");
    expect(html).toContain("<td>Body width</td>");
    expect(html).toContain("<td>38.00 mm</td>");
    // The separator row itself must never be rendered as data.
    expect(html).not.toContain("---");
  });

  it("renders the Strings table (a second, independent table) correctly", () => {
    expect(html).toContain("<th>Gauge</th>");
    expect(html).toContain("<td>0.036 in</td>");
    expect(html).toContain("<td>0.914 mm</td>");
    const tableCount = (html.match(/<table>/g) ?? []).length;
    expect(tableCount).toBe(2);
  });

  it("renders the Validation bullet list as a real <ul>/<li>", () => {
    expect(html).toContain("<ul><li>All parameter checks passed.</li></ul>");
  });

  it("renders the closing Notice paragraph as plain text", () => {
    expect(html).toContain("<p>The calculated geometry must be verified");
  });

  it("never leaves raw Markdown table/heading syntax visible as text", () => {
    expect(html).not.toMatch(/\|---/);
    expect(html).not.toMatch(/^##? /m);
  });
});

describe("renderReportMarkdownToHtml — edge cases", () => {
  it("escapes HTML-significant characters in cell/paragraph content", () => {
    const html = renderReportMarkdownToHtml("Body <width> & \"height\"");
    expect(html).toContain("&lt;width&gt;");
    expect(html).toContain("&amp;");
    expect(html).toContain("&quot;");
    expect(html).not.toContain("<width>");
  });

  it("renders a validation error/warning list correctly (not just the all-clear message)", () => {
    const markdown = [
      "## Validation",
      "",
      "- ERROR: Groove too big.",
      "- WARNING: Minimum wall is tight.",
    ].join("\n");
    const html = renderReportMarkdownToHtml(markdown);
    expect(html).toContain("<li>ERROR: Groove too big.</li>");
    expect(html).toContain("<li>WARNING: Minimum wall is tight.</li>");
  });

  it("does not throw on empty input", () => {
    expect(() => renderReportMarkdownToHtml("")).not.toThrow();
    expect(renderReportMarkdownToHtml("")).toBe("");
  });

  it("does not throw on unrecognized content — degrades to a paragraph rather than crashing", () => {
    expect(() => renderReportMarkdownToHtml("```some fenced code block```")).not.toThrow();
  });
});
