# Runtime trace

Run a trace on macOS with an explicit output outside the analyzed bundle:

```bash
python tools/trace_runtime.py "dist/ZeroRodCAD Desktop.app" \
  --profile startup-test --output /tmp/zerorod-startup.json
```

Profiles are `startup-test`, `preview-probe` and `export-probe`. Native dyld and Qt plug-in
diagnostics are enabled by default; `--no-dyld` and `--no-qt-debug` disable them. `--timeout`
controls the run. `--keep-raw` copies raw hook/stdout/stderr diagnostics beside the JSON into a
dedicated external directory; otherwise raw material is deleted.

The runtime hook is opt-in and its environment names are centrally defined in
`runtime/schema.py`. Users should invoke the controller rather than setting them manually. Without
the opt-in switch the hook installs no audit hook, writes no snapshot and emits no trace output.

An observation proves that an item was used in the exercised profile. Missing observation is not
proof of non-use. Crashes, forced termination, missing hook end records and recorder/parser errors
set `incomplete`; evidence already received is retained.

The former `tools/trace_runtime_imports.py` is a compatibility entry point. It prints a migration
notice and delegates to this controller.
