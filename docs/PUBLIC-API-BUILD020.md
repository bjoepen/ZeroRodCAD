# Build 020 Public API

The supported package-level API contains exactly four functions:

```python
from zerorod_analysis import (
    analyze_bundle,
    calculate_bundle_health,
    generate_action_plan,
    generate_reports,
)
```

- `analyze_bundle(app_bundle, *, cache_dir=..., use_cache=True, scan_filter=None)` performs the
  established scanner, Mach-O, and dead-library analysis without modifying the bundle.
- `generate_reports(analysis, output_dir)` writes the established dead-library reports.
- `generate_action_plan(analysis)` returns the established optimization-plan Markdown.
- `calculate_bundle_health(analysis)` returns the established health evaluation.

All subpackages and data types are implementation details. They remain importable where needed
for internal code and compatibility, but they are not added to `zerorod_analysis.__all__`.

## M2 pipeline compatibility

Build 020 M2 routes `analyze_bundle()` through the internal `AnalysisPipeline`. Its signature,
defaults, runtime result (`DeadLibraryAnalysisResult`, internally aliased as `AnalysisResult`), and
errors from the underlying analyzers remain compatible. Pipeline classes and stages are not
top-level exports. Report contents and filenames are unchanged.
