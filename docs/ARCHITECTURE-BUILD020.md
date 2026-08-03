# Build 020 Architecture

Build 020 M1 extracts the bundle analyzer from the development-tool namespace into the
standalone `zerorod_analysis` package. The extraction does not change analysis algorithms,
reports, command-line arguments, or user-visible behavior.

The dependency direction is now:

```text
tools/scan_bundle.py ───────────────┐
tools/bundle_analyzer/* wrappers ───┼──> src/zerorod_analysis
future desktop integrations ────────┘
```

`zerorod_analysis` is independent of the desktop application. It imports neither GUI modules
nor PySide6. Scanner data flows to Mach-O dependency analysis, dead-library analysis, advisory
logic, and finally report generation. Internal modules never import from `tools`.

The legacy package contains compatibility wrappers only. They re-export the objects from the
new package, preserving object identity and every established import path.

## Final architecture

```text
analyze_bundle -> AnalysisPipeline -> AnalysisResult + PipelineMetrics
generate_reports -> ReportEngine -> JSON / Markdown / DOT + ReportMetrics
```

The pipeline order is Scanner, Mach-O, Dead Library, Advisor. Each stage and selected renderer runs
once. Metrics belong to one run and do not change analysis or report content. Reporting remains
outside the pipeline and never modifies the application bundle.

Build metadata is defined only in `build_metadata.py`. Scanner 2.0's versioned cache remains the
only persistent cache. The internal benchmark uses temporary cache and report directories.
