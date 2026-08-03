# Migration to Build 020 M2

No caller migration is required. These supported calls remain unchanged:

```python
from zerorod_analysis import (
    analyze_bundle,
    calculate_bundle_health,
    generate_action_plan,
    generate_reports,
)
```

Existing `tools.bundle_analyzer` imports continue to delegate to the same implementation objects.
The Scanner CLI retains its arguments, version output, exit behavior, and report filenames.

`AnalysisPipeline`, `PipelineContext`, stage classes, and pipeline exceptions are internal M2
architecture. They are intentionally absent from `zerorod_analysis.__all__`. Integrations should
continue to call `analyze_bundle()` rather than construct the pipeline directly.

M2 changes orchestration only. It does not alter detection, risk, health, action-plan, or report
behavior.
