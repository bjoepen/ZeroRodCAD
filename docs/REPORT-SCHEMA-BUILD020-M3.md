# Build 020 M3 Report Schema

The engine manifest schema ID is:

```text
zerorod-analysis/report/v1
```

`ReportManifest` is an internal in-memory contract containing that ID and ordered rendered files.
It is not a new output file.

The established `dead-libraries.json` payload remains at `schema_version: 2`. Its keys and value
types are unchanged: bundle root, bundle health, summary, potential savings, and findings. This
existing version is retained rather than adding a breaking envelope merely to expose the engine
manifest ID.

The historical Scanner and Mach-O JSON documents did not contain schema fields. M3 preserves their
bytes and documents them as legacy projections under the v1 engine manifest. A future incompatible
payload change requires a new documented payload version; optional backward-compatible fields may
be added only with contract tests and migration notes.
