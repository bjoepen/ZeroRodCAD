# Migration to Build 020 M3

No public caller migration is required. The four top-level functions, parameters, defaults, return
types, report names, and compatibility import paths remain available.

`generate_reports(result, output_dir)` now delegates to `ReportEngine`. Existing internal callers
of `write_dead_library_reports`, `write_macho_reports`, and `write_scanner_reports` keep their
signatures and tuple ordering while using the same engine.

The report engine, request models, registry, and renderers are internal and intentionally absent
from `zerorod_analysis.__all__`. Applications should keep using the public functions. M3 introduces
no HTML/PDF output and no functional analysis change.
