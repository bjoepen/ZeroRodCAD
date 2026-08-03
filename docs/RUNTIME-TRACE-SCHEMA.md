# Runtime trace schema

The single schema identifier is `zerorod-analysis/runtime-trace/v1`, defined only in
`src/zerorod_analysis/runtime/schema.py`. The build identifier comes only from
`zerorod_analysis.build_metadata`.

A trace contains schema/build/runtime metadata, UTC ISO-8601 start and end timestamps, profile,
exit status/code, timeout and incomplete flags, evidence lists, event counters and an optional
error. Evidence lists are divided into Python modules, native Python extensions, loaded dylibs or
frameworks, and Qt plug-ins.

Each evidence item has an identity, kind, status, unique sorted sources, accumulated event count,
optional bundle-relative path and sorted details. Status meanings:

- `observed`: directly seen by audit, snapshots, dyld or Qt diagnostics.
- `inferred`: supported by a static source but not directly seen (reserved for compatible input).
- `unresolved`: a real event whose private or component identity cannot safely be resolved.

Merge is independent of input order. Identical kind/identity pairs combine counts and sources;
`observed` outranks `inferred`, which outranks `unresolved`. Conflicting bundle paths remain in
details. JSON uses sorted keys/lists, UTF-8 and a trailing newline, so identical traces serialize to
identical bytes.
