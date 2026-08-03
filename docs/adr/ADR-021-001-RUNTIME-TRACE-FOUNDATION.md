# ADR-021-001: Runtime trace foundation

Status: Accepted

## Context

Static analysis cannot prove dynamically imported Python modules, native loader activity or Qt
plug-in selection. Runtime evidence can contain private paths and may be incomplete after crashes.
Instrumentation must not affect ordinary application runs or Build 020 recommendations.

## Decision

Use one internal immutable schema and one macOS subprocess controller. Install `sys.addaudithook`
and start/end `sys.modules` snapshots in the existing PyInstaller runtime hook only under an
explicit opt-in. Supplement them with tolerant dyld and Qt stderr parsers. Normalize paths before
durable JSON, preserve unresolved events, merge deterministically and write atomically outside the
bundle. Use process groups and a TERM/KILL timeout sequence.

Do not monkeypatch importlib, add a primary `MetaPathFinder`, expose a new top-level API or consume
the trace in analysis decisions during M1.

## Consequences

The normal frozen startup keeps its existing Qt path behavior and receives no tracing overhead.
The three profiles provide reproducible startup, lazy preview and lazy export evidence. Audit hooks
cannot see events before installation, dyld/Qt text is diagnostic rather than a stable protocol,
and `atexit` may be absent. Therefore traces explicitly represent incomplete runs, and absence of
evidence is never treated as evidence of non-use. M2 owns any later evidence-to-library mapping.
