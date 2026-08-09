# TE-002.2B — Conclusion

## Which of TE-002.2A's five candidates were actually safe to act on

All five. Each was investigated individually with real evidence before any change, changed as an
isolated variable, rebuilt for real, and functionally validated — none were forced through on
"NOT OBSERVED" alone.

| Candidate | Outcome | Savings |
|---|---|---:|
| Duplicate onefile sidecar | ACCEPTED — packaging-config removal (`externalBin`) | 135.45 MiB |
| Duplicate dylibs | ACCEPTED — root cause found (Tauri's resource copy dereferences PyInstaller's own dedup symlinks); fixed with a deterministic, hash-gated post-bundle script | 93.90 MiB |
| llvmlite (+ numba together) | ACCEPTED — import-origin traced to an unreachable CadQuery visualization feature, confirmed by both static analysis and a direct runtime check | 128.27 MiB |
| numba | ACCEPTED (with llvmlite, structurally paired) | (included above) |
| scipy | ACCEPTED — independently tested, same root cause | 35.45 MiB |

## Why this went further than TE-002.2A's own candidate list expected

TE-002.2A flagged the dylib duplication as "a PyInstaller packaging/config investigation... not
performed here." The actual investigation found something more specific and more useful than a
PyInstaller spec tweak: PyInstaller had already solved this via symlinks, and Tauri's own bundler
was silently undoing that solution on every build. This is a better outcome than a spec-level
`--exclude-binary` filter would have been — it fixes the real cause instead of working around a
symptom, and it is verifiably safe (hash-gated, dyld-verified) rather than merely "probably fine."

## Scientific discipline honored

No candidate was forced to be removable. All five happened to be genuinely safe, evidenced by:
real rebuilds (not hand-edited artifacts), full functional/regression test suites passing at each
stage (48/48 sidecar, 241/1-skip full repo, 17/17 Rust, 30/30 frontend), and a real performance/
memory benchmark showing no regression. Nothing was rolled back — every experiment converged to
an accept, and each is documented with its own before/after numbers rather than a single blended
claim.

## What was explicitly not touched

OCP, casadi, nlopt, numpy, ezdxf — all REQUIRED/OBSERVED per TE-002.2A, out of scope here, and
none of the five accepted optimizations affects them (byte-identical presence confirmed via
`find`/`otool` sampling during validation).

## Architecture impact

**NONE.** Every change in TE-002.2B is a packaging/dependency-exclusion change: a Tauri bundle
config key removed, a post-bundle packaging script, and two PyInstaller `.spec` exclude entries.
No IPC boundary, process-lifecycle logic, mesh contract, or protocol schema was touched. TE-002 /
TE-002.1's architectural decisions (Tauri v2 + Python sidecar + Three.js, persistent + onedir as
the sole runtime strategy) stand exactly as before.

## Recommended next step

Human validation of the optimized `.app` (`HUMAN-VALIDATION.md`) — the automated evidence here
closes the "does the shipped artifact actually work" question at the process/protocol level, the
same level TE-002.1 itself validated at; the interactive WebView click-through remains outside
this environment's automation reach (macOS Accessibility permissions), same limitation as every
prior TE in this series.
