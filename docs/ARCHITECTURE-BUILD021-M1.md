# Build 021 M1 architecture

Build 021 M1 introduces a read-only runtime evidence boundary. The platform-neutral internal
package `zerorod_analysis.runtime` owns immutable models, normalization, merging and deterministic
serialization. It has no Qt or desktop dependency and is not added to the top-level public API.

`tools/trace_runtime.py` is the only controller. It validates an app bundle, launches its
executable in a separate process group, combines hook, dyld and Qt observations and writes the
normalized trace outside the bundle. `packaging/macos/runtime_hook.py` retains its existing Qt path
setup and installs recording only when the central opt-in environment switch is present.

The three profiles are `startup-test`, `preview-probe` and `export-probe`. All launch the existing
non-interactive app startup path. In an opted-in trace process only, the hook runs the existing
headless preview or controlled STL/STEP export stimulus during orderly shutdown. Export artifacts
live in the controller's external temporary directory and are removed with it.

M1 only records evidence. It does not feed `LibraryUnit`, `AnalysisPipeline`, `ReportEngine`,
confidence, recommendations, risk or bundle health. A separate M2 mapping layer may consume this
schema later, while retaining unresolved observations.
