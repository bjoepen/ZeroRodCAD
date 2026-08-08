# TE-002.2A — Bundle Composition

## Measured size (units made explicit, not blended)

| Measure | Value |
|---|---|
| Apparent size (`find`+`stat`, sum of real file sizes) | 706,051,017 bytes = **673.34 MiB** = 706.05 MB (decimal) |
| `du -sh` (disk usage, 512-byte blocks) | 674M |
| `du -sk` | 690,268 KB = 674.09 MiB |
| Scanner 2.0 (`scanner2-report.md`, byte sum) | 673.34 MiB — agrees with the `find`+`stat` figure |
| File count | 372 files, 96 directories, 0 symlinks, 338 Mach-O files |

The user's "~700 MB" is correct in decimal-MB terms (706.05 MB) and close in MiB terms (673–674
MiB) — not an overstated number, just a different unit than the MiB figures used throughout the
rest of this TE series. All figures below use MiB for direct comparability with TE-001.2's
380.12 MiB baseline (same unit that number was reported in).

## Top-level bundle map

| Area | Files | Size |
|---|---:|---:|
| `Contents/MacOS` | 2 | 148.49 MiB |
| `Contents/Resources` | 291 (Scanner 2.0 "Resources" bucket) + 76 (OCP) + 2 (casadi) = 369 | 299.84 + 216.03 + 8.98 = 524.85 MiB |
| `Contents/Frameworks` | — | does not exist |
| `Contents/PlugIns` | — | does not exist |
| `Contents/Info.plist` | 1 | 992 bytes |

`Contents/MacOS` breaks down into exactly two files: the Rust/Tauri/frontend executable
(`te002-tauri`, 13.04 MiB) and a **second, full copy of the Python sidecar**, packaged onefile
(`zerorod-engine`, 135.45 MiB — TE-002's original fallback path, still wired up and callable via
`requestPreviewOneShot`).

`Contents/Resources` contains the app icon (0.11 MiB) and the onedir-packaged sidecar
(`zerorod-engine-onedir/`, 525.48 MiB — the TE-002.1-recommended default path).

**Headline finding**: the two sidecar copies together (135.45 + 525.48 = 660.93 MiB) account for
**98.15%** of the entire app's size. Tauri/Rust/frontend itself is 13.04 MiB — under 2%. This is
not a Tauri-is-heavy story; it is a "the Python CAD engine dependency set is bundled twice" story.

## Top 5 largest files (of 372)

| File | Size |
|---|---:|
| `Resources/zerorod-engine-onedir/_internal/OCP/OCP.cpython-313-darwin.so` | 139.54 MiB |
| `MacOS/zerorod-engine` (onefile sidecar, opaque compressed archive) | 135.45 MiB |
| `Resources/zerorod-engine-onedir/_internal/llvmlite/binding/libllvmlite.dylib` | 122.78 MiB |
| `Resources/zerorod-engine-onedir/zerorod-engine` (onedir executable) | 16.16 MiB |
| `MacOS/te002-tauri` (Rust/Tauri + embedded frontend) | 13.04 MiB |

## Onedir sidecar breakdown (`_internal/`, 509.32 MiB — the only fully attributable, uncompressed copy)

| Component | Size | % of `_internal` |
|---|---:|---:|
| OCP (`.so` + `.dylibs/`) | 216.18 MiB | 42.5% |
| llvmlite (single dylib, numba's LLVM JIT backend) | 122.78 MiB | 24.1% |
| Other native shared libraries at `_internal/` root (mostly OpenCASCADE `TK*.dylib`, plus `libcasadi`, `libcrypto`/`libssl`, image codec libs) | 89.98 MiB | 17.7% |
| scipy | 31.75 MiB | 6.2% |
| Python runtime (`Python.framework` + `Python` + `python3.13` stdlib/lib-dynload) | 20.57 MiB | 4.0% |
| casadi (Python package) | 8.98 MiB | 1.8% |
| numpy | 6.55 MiB | 1.3% |
| CadQuery + ezdxf + nlopt + numba + fontTools + `base_library.zip` + dist-info/misc | ~12.5 MiB | 2.4% |

Onefile's 135.45 MiB is a compressed, opaque, self-extracting archive of the same underlying
build (same `.spec` hiddenimports/excludes as onedir, per TE-002.1's `Runtime-Variants.md`) — it
was not unpacked for this evaluation (read-only, no new tooling), so it cannot be broken down at
the same file level; its size is consistent with compressing ~509 MiB of largely dylib/`.so`
content to ~26% (a normal ratio for already-compiled native binaries, which don't compress as well
as text but still shrink meaningfully).

## OCP, compared descriptively to TE-001.2

TE-001.2's PySide6 bundle: OCP = 216.03 MiB (78 files). TE-002.1's Tauri bundle: OCP = 216.18 MiB
(76 files, Scanner 2.0 count). Effectively identical (Δ +0.15 MiB) — expected, since both reuse
the same patched `cadquery-ocp-novtk` 7.9.3.1.1 build. OCP.cpython-313-darwin.so alone is
139.54 MiB, the single largest file in the bundle.

## VTK — confirmed 0, three independent methods

| Method | Result |
|---|---|
| `find -iname "*vtk*" -o -iname "*IVtk*"` over the whole `.app` | 0 matches |
| Scanner 2.0 `section_sizes["VTK"]` / `section_counts["VTK"]` | 0 bytes / 0 files |
| Hash-identity of the bundled onedir binary with TE-002.1's already runtime-traced copy (`vtk_evidence()` → `[]`) | Confirmed identical (SHA-256 match), evidence carries over |

Known false positive (same as every prior TE in this series): `cadquery.occ_impl.exporters.vtk`
is a real, correctly-named module inside the patched CadQuery — present, but correctly not counted
as VTK evidence by the path-segment-based heuristic used throughout this TE series.

## PySide6 / Qt — confirmed 0

| Method | Result |
|---|---|
| `find -iname "*PySide*" -o -iname "*Qt*"` over the whole `.app` | 0 matches |
| Scanner 2.0 `section_sizes["PySide6"]` / `["Qt"]` | 0 bytes / 0 files |

## Tauri / Rust / Frontend

`Contents/MacOS/te002-tauri`: 13.04 MiB total. The frontend's built assets
(`experiments/te002-tauri/frontend/dist/`) are only **540 KB** and are embedded into this single
Rust binary at build time (no loose `.js`/`.html`/`.css` files exist anywhere in the bundle) — so
essentially all 13.04 MiB is the Tauri/Rust/WRY runtime itself, not the frontend. Relative to the
Python sidecar's ~660 MiB (both copies), the GUI layer is negligible.

## Duplicate analysis (hash-based, not filename-based)

A full-bundle SHA-256 comparison among same-sized files (≥4 KB, 160 size-collision candidates
hashed) found **77 duplicate groups, 93.90 MiB reclaimable** (one copy's worth) — entirely inside
the onedir sidecar (the onefile copy is a compressed archive and could not be included in a
byte-level scan without unpacking it, not attempted here).

Dominant pattern (74 of the 77 groups): OpenCASCADE `TK*.dylib` files exist **twice** —
once directly under `_internal/` (PyInstaller's own dependency-walker collection) and once again
under `_internal/OCP/.dylibs/` (the OCP wheel's own bundled-`.dylibs` directory, a standard
`delocate`/`auditwheel`-style convention). Both copies are byte-identical (verified by hash, not
assumed from matching filenames) — this is the single largest reclaimable-within-onedir group,
about 75 MiB of the 93.90 MiB total. Other groups: `Python`/`Python.framework/Python`/
`Python.framework/Versions/3.13/Python` (the same 4.9 MiB binary present 3×, 9.57 MiB reclaimable),
`libcasadi.3.7.dylib` present both at `_internal/` root and under `_internal/casadi/` (7.96 MiB),
and one `libc++.1.0.dylib` pair under `casadi/` vs. `OCP/.dylibs/` (1.02 MiB). One name-collision
was checked and found to be a genuine version difference, not a duplicate:
`OCP/.dylibs/libc++.1.0.dylib` differs in content from the root-level `libc++.1.0.dylib` (both
exist, this is the one exception among the 75 name-matched pairs).

This 93.90 MiB is separate from, and much smaller than, the ~135 MiB "duplicate sidecar packaging"
finding above (onefile vs. onedir) — that one is a packaging-strategy artifact, not a byte-level
duplicate (compressed archive vs. uncompressed tree cannot be hash-compared directly).

## Dead-library analyzer — informational only, not actionable (same caveat as TE-001.1/TE-001.2)

Bundle Health 69/100 (fair), 402.67 MiB flagged as potential savings. Carries the same known
false-positive TE-001.1/TE-001.2 already documented for this tool: it flags
`OCP.cpython-313-darwin.so` itself (139.54 MiB, the CAD kernel) as "SAFE REMOVE" with "No Mach-O
dependency was found" — almost certainly wrong, since OCP is confirmed load-bearing by every prior
TE. The score and size totals are informational context only; the specific removal list is not
treated as evidence here, consistent with prior TEs' treatment of the same tool.
