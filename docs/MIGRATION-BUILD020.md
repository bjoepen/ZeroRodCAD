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

The Scanner CLI keeps its existing arguments, defaults, exit codes, and report formats. Build
020 M1 introduces no feature, analyzer-rule, or user-behavior change.
