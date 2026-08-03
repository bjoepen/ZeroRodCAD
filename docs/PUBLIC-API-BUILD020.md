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
