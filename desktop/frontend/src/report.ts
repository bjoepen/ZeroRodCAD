// Build 025 M3 — the Instrument Report IPC boundary and a minimal,
// hand-rolled renderer for the specific Markdown subset
// `zerorodcad.report.build_report` actually produces (headings, one table
// per section, a bullet list, plain paragraphs — see
// docs/contracts/ZEROROD-PARAMETERS-V1.md's `report` command section and
// `src/zerorodcad/report.py`). Deliberately not a general Markdown parser
// or a new dependency (§35 of the mandate: "do not add a charting/report
// framework just to display report values") — this renders exactly the
// fixed, small set of constructs the canonical report source emits, not
// arbitrary Markdown.

import { invoke } from "@tauri-apps/api/core";
import { buildParametersRequest, type ZeroRodParametersValues } from "./parameters";

export interface ReportResult {
  markdown: string;
}

/** Round-trips the sidecar's `report` command (via `engine_report`) for an
 * explicit zerorod-parameters/v1 value set — same request shape as
 * `requestPreviewMeshWithParameters` (`parameters.ts`). The caller decides
 * which values to pass; per §18 of the mandate that must always be
 * `accepted`, never a draft (report_panel.ts enforces this, this function
 * just forwards whatever it's given). */
export async function requestReport(values: ZeroRodParametersValues): Promise<ReportResult> {
  return await invoke<ReportResult>("engine_report", {
    parameters: buildParametersRequest(values),
  });
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isTableRow(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|");
}

/** A Markdown table separator row, e.g. `|---|---:|` or `| :--- | ---: |`. */
function isTableSeparatorRow(line: string): boolean {
  return /^\|(\s*:?-+:?\s*\|)+$/.test(line.trim());
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

/** Pure — converts `build_report()`'s Markdown into safe, structured HTML
 * (real `<table>`/`<h2>`/`<h3>`/`<ul>` elements, not a raw-text dump — §20
 * of the mandate). Every line falls into exactly one of: an H1 (`# `,
 * rendered `<h2>` — the report panel supplies its own page-level heading),
 * an H2 (`## `, rendered `<h3>`), a table (a row immediately followed by a
 * separator row starts one; consecutive `|...|` rows after that are its
 * body), a bullet list item (`- `), or a plain paragraph. Unrecognized
 * input degrades to paragraphs rather than throwing — this must never
 * crash the report view over a future wording change in `build_report()`. */
export function renderReportMarkdownToHtml(markdown: string): string {
  const lines = markdown.split("\n");
  const html: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "") {
      i++;
      continue;
    }

    if (line.startsWith("## ")) {
      html.push(`<h3>${escapeHtml(line.slice(3).trim())}</h3>`);
      i++;
      continue;
    }

    if (line.startsWith("# ")) {
      html.push(`<h2>${escapeHtml(line.slice(2).trim())}</h2>`);
      i++;
      continue;
    }

    if (line.startsWith("- ")) {
      const items: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        items.push(`<li>${escapeHtml(lines[i].slice(2).trim())}</li>`);
        i++;
      }
      html.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    if (isTableRow(line) && i + 1 < lines.length && isTableSeparatorRow(lines[i + 1])) {
      const headerCells = splitTableRow(line);
      i += 2; // header row + separator row
      const bodyRows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i])) {
        bodyRows.push(splitTableRow(lines[i]));
        i++;
      }
      const headHtml = `<thead><tr>${headerCells
        .map((cell) => `<th>${escapeHtml(cell)}</th>`)
        .join("")}</tr></thead>`;
      const bodyHtml = `<tbody>${bodyRows
        .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
        .join("")}</tbody>`;
      html.push(`<table>${headHtml}${bodyHtml}</table>`);
      continue;
    }

    html.push(`<p>${escapeHtml(line.trim())}</p>`);
    i++;
  }

  return html.join("");
}
