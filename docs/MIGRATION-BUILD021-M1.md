# Migration to Build 021 M1

Analyzer build metadata changes from Build 020 M4 to Build 021 M1. Existing scanner and benchmark
entry points continue to source their version from `build_metadata.py`; the runtime controller does
the same.

Replace the old no-argument VTK-only command:

```bash
python tools/trace_runtime_imports.py
```

with an explicit bundle and external output:

```bash
python tools/trace_runtime.py APP_BUNDLE --profile preview-probe --output TRACE_JSON
```

The old file remains as a delegating compatibility shim and has no recorder, merge or serializer.
Build 020's top-level analysis API and all recommendation, risk and health behavior are unchanged.
M2 may add an explicit consumer of runtime traces; M1 does not apply them to analysis results.
