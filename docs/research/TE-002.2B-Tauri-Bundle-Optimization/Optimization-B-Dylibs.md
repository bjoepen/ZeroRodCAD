# TE-002.2B — Optimization B: Duplicate Dylib Investigation

## The real root cause (found by direct inspection, not assumed)

TE-002.2A found 77 hash-identical groups (93.90 MiB) between `_internal/` and
`_internal/OCP/.dylibs/` and correctly did not guess why. Investigation here:

1. A **fresh, clean** PyInstaller onedir build (`--clean`, new `--workpath`) of the *unmodified*
   spec, same environment, was compared file-by-file against the previously-built onedir tree. The
   fresh build's `_internal/libTKBin.7.9.3.dylib` (and all 77 other "duplicate" paths) turned out
   to be **relative symlinks** to `_internal/OCP/.dylibs/libTKBin.7.9.3.dylib`, not real files —
   verified with `ls -la` (`lrwxr-xr-x ... -> OCP/.dylibs/libTKBin.7.9.3.dylib`) and confirmed for
   every one of the 77 TE-002.2A groups, including the 3-way `Python`/`Python.framework/Python`
   chain (both symlinks to the one real `Python.framework/Versions/3.13/Python`).
2. **PyInstaller's own onedir COLLECT step already deduplicates these binaries via symlinks** — a
   standard `delocate`/`auditwheel`-style convention the OCP wheel and PyInstaller's binary
   TOC-merging cooperate on. The standalone `experiments/te002-tauri/onedir-dist/zerorod-engine`
   output has **zero duplicate bytes on disk** for this entire set.
3. **Tauri's `bundle.resources` copy step dereferences symlinks** while copying
   `resources/zerorod-engine-onedir/` into the built `.app`'s `Contents/Resources/` — turning every
   one of those 78 symlinks back into a full real-file copy. This is where TE-002.2A's 93.90 MiB
   of "duplicate" bytes actually comes from: it is a **Tauri-bundling artifact**, not a PyInstaller
   packaging defect and not something OCP or the sidecar spec did wrong.

(A second, unrelated bug was found and worked around during this investigation: Tauri's resource
copy — and, separately, the `target/release/bundle` output directory itself — merge-copy without
deleting stale files, so a resource update that removes files requires deleting
`target/release/{bundle,zerorod-engine-onedir}` first, or the stale files linger. Not itself an
optimization; just a build-hygiene trap this evaluation had to route around to get honest
measurements. `scripts/validate-te0022b-bundle-optimization.sh` purges these paths before each
build for exactly this reason.)

## Fix: restore the symlinks, deterministically, after bundling

`tools/poc/tauri/dedup_bundle_dylibs.py` — given the pristine PyInstaller source tree (which still
has the real symlinks) and the built `.app`'s dereferenced copy, it re-applies each symlink from
source onto target, but **only** after confirming (by SHA-256, not just size or filename) that the
target file's current dereferenced content still matches the symlink's resolved source content. A
pair that differs is left alone and reported — this preserves TE-002.2A's own documented exception
(`OCP/.dylibs/libc++.1.0.dylib` vs. `casadi/libc++.1.0.dylib`: a genuine version difference, not a
duplicate). This is a deterministic, reproducible packaging-time script, not a one-off `rm`: it can
be re-run against any clean build and always converges on the same result, and it is wired into
`scripts/validate-te0022b-bundle-optimization.sh` as a required post-build step.

## Measurement (dedup applied alone, onefile still present, i.e. before Optimization A)

| | Bytes | MiB | Files |
|---|---:|---:|---:|
| Baseline | 706,051,017 | 673.34 | 372 |
| B only | 607,585,417 | 579.43 | 294 |
| **Savings** | **98,465,600** | **93.90** | **78** |

Matches TE-002.2A's own "93.90 MiB reclaimable" estimate almost exactly — the fresh-build/symlink
investigation didn't just find a *different* number, it explains and reproduces the *exact* one
already measured.

## Validation

`dedup_bundle_dylibs.py --json` output: `relinked_count: 78`, `skipped_different_content: []` (no
false positives — every relink was hash-verified byte-identical first). After relinking, the
bundled sidecar binary was driven through a real `preview` request via the exact
`Contents/Resources/zerorod-engine-onedir/zerorod-engine` binary — dyld correctly resolves the
restored symlinks at runtime (proven, not assumed: mesh output matches the 720+146-vertex
reference exactly). Full validation matrix: `Runtime-Validation.md`.

## Accepted

Dylib deduplication is **ACCEPTED**, implemented as a deterministic post-bundle packaging script
(not spec-level, since the duplication is introduced by Tauri's bundler, not by the PyInstaller
spec). Real, measured, isolated savings of 93.90 MiB with zero content risk (hash-gated).
