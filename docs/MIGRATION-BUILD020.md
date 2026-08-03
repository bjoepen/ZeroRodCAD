# Migration to Build 020

No immediate migration is required. Existing imports continue to work:

```python
from tools.bundle_analyzer.deadlibs import DeadLibraryAnalyzer
```

New integrations should use the package-level API:

```python
from zerorod_analysis import analyze_bundle, generate_reports

analysis = analyze_bundle("dist/ZeroRodCAD.app")
generate_reports(analysis, "build/reports/dead-libraries")
```

Code that intentionally uses internal data types may migrate from
`tools.bundle_analyzer.<module>` to `zerorod_analysis.<module>`. The compatibility layer remains
available so migration can be performed independently of this release.

The Scanner CLI keeps its existing arguments, defaults, exit codes, and report formats. Build 020
introduces no analyzer-rule or user-behavior change. `AnalysisResult` now carries optional per-run
metrics and already computed intermediate references; existing construction and field access remain
valid because all additions have defaults.

Developers may benchmark a bundle with `tools/benchmark_analysis.py`. This diagnostic interface is
not exported from the stable top-level API and is not required for application integrations.
