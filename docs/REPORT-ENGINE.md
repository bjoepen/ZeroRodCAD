# Unified Report Engine

`ReportEngine` receives only a completed `AnalysisResult` and a data-only `ReportRequest`. Its
immutable `RendererRegistry` explicitly registers JSON, Markdown, and DOT renderers. Registry names
and formats must be unique; no plugin scanning or magic imports occur.

Renderers return `RenderedReport` values and perform no file operations or analysis. The engine
selects requested formats, invokes each selected renderer once, renders everything before writing,
rejects path collisions and traversal, prevents output inside the analyzed `.app`, and writes each
UTF-8 file using a temporary sibling plus atomic `os.replace`.

## Existing outputs

- JSON: `dead-libraries.json`, `macho-dependencies.json`, `scanner2-inventory.json`
- Markdown: `dead-libraries.md`, `bundle-size-analysis.md`, `optimization-report.md`,
  `optimization-plan.md`, `macho-dependencies.md`, `macho-unresolved.md`, `scanner2-report.md`
- DOT: `macho-dependencies.dot`

`generate_action_plan()` uses the same Markdown renderer in memory and performs no write.

## Extension

A future renderer implements `ReportRenderer`, owns one unique format, and is explicitly added to a
registry. HTML and PDF could follow this contract later, but M3 implements neither format and adds
no runtime dependency.
