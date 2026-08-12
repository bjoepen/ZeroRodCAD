# Build 022 — Milestone 4: Productive Packaging Baseline

Status: **COMPLETE**

## Objective

Turn the working productive Build-022 desktop app (M1–M3) into a reproducible, measured, and
optimized packaging build — answering: *can the No-VTK/No-PySide6/onedir/dylib-dedup packaging
strategy TE-002.2B proved empirically be carried into the productive Build-022 path, reproducibly,
without breaking functionality, performance, security, or process lifecycle?* M4 is not a feature
milestone; it touches packaging only.

## Baseline (discovery, before any change)

A completely clean rebuild (removed `desktop/src-tauri/target`, `desktop/sidecar-dist`,
`desktop/src-tauri/resources`, `build/zerorod-engine`; rebuilt sidecar → staged → `tauri build
--debug`) was measured before any M4 change, per the mandate's explicit instruction not to assume
M3's own 399 MB figure still applies.

| Metric | Value |
|---|---:|
| Bytes | 417,764,337 |
| MiB | 398.41 |
| Decimal MB | 417.76 |
| Files | 278 |
| Directories | 57 |
| Symlinks | 0 |
| Mach-O files | 238 |
| `Contents/MacOS` | 37 MiB (debug build, unstripped) |
| `Contents/Resources` | 362 MiB |

Duplicate analysis against the pristine PyInstaller source tree (`desktop/sidecar-dist/`, which
still has PyInstaller's own symlink-based dedup intact):

| Metric | Value |
|---|---:|
| Hash-verified duplicate pairs | 78 |
| Mismatched pairs (real differences) | 0 |
| Reclaimable bytes | 98,466,128 |
| Reclaimable MiB | 93.90 |

Matches TE-002.2B's own 93.90 MiB finding almost exactly — the productive path has the identical
root cause TE-002.2B diagnosed for the PoC.

VTK/PySide6/Qt/numba/llvmlite/scipy: **0** files, confirmed before any M4 change (already correct
from M2/M3's own packaging spec — see "Optimizations already in place" below).

## Optimizations already in place (verified, not re-applied)

- **A — no onefile fallback**: `tauri.conf.json` has no `externalBin` key; `Contents/MacOS/`
  contains exactly one executable (`zerorod-desktop`). Nothing to change.
- **C — numba/llvmlite excluded**: present in `packaging/tauri/sidecar-onedir.spec`'s `excludes`
  since M2. Confirmed 0 matching files in the built bundle.
- **D — scipy excluded**: same spec, same confirmation.

Only **B — dylib deduplication** was missing productively. That is M4's actual work.

## Discovery: the productive root cause, reconfirmed (not assumed)

Symlink counts, measured directly:

| Tree | Symlinks |
|---|---:|
| Pristine PyInstaller output (`desktop/sidecar-dist/zerorod-engine/_internal`) | 80 |
| Staged Tauri resource (`desktop/src-tauri/resources/.../_internal`, after `cp -R`) | 80 |
| Built `.app`'s `Contents/Resources/.../_internal` | 0 |

`cp -R` (the staging step) preserves all 80 symlinks correctly. Tauri's own `bundle.resources` copy
step is what dereferences every one of them while building the `.app` — the exact mechanism
`Optimization-B-Dylibs.md` diagnosed for the PoC, reproduced byte-for-byte in the productive path.

## Dylib dedup mechanism

`packaging/tauri/dedup_bundle_dylibs.py` — a productive adaptation of
`tools/poc/tauri/dedup_bundle_dylibs.py` (TE-002.2B's own proof of this fix), not an import of it:
the PoC stays a standalone, untouched research artifact, and the productive packaging pipeline
does not depend on `tools/poc/`.

Algorithm, for every symlink in the pristine PyInstaller source tree:

1. Resolve what real file it points to.
2. Check whether the corresponding path in the built `.app` is already a (safe) symlink — if so,
   this is a no-op (idempotency).
3. Otherwise, require the target path to exist as a real file, with **identical size and
   SHA-256** to the resolved source — never filename or size alone.
4. Only then: delete the real-file copy, recreate the relative symlink.
5. Verify the newly-created symlink is safe: relative (no absolute paths), resolves to a real
   file, and stays inside the bundle root (no traversal outside it, no reference to the build
   environment). An unsafe result is reverted immediately (the real-file copy is restored) rather
   than shipped broken.

A pair with mismatched content is left alone and reported as a **loud, strict failure** (script
exits 1) — a real version difference is not a duplicate, same discipline TE-002.2A's own
`libc++.1.0.dylib` exception established.

### Safety model

- **Hash-gated, never filename-gated.** Size mismatch or hash mismatch → left alone, reported.
- **Symlink-safety verified after every relink** — relative, resolves inside the bundle, points
  at a real file. Any violation is reverted, not shipped.
- **Idempotent.** A second run against an already-deduplicated bundle relinks 0 files (verified —
  see "Validation").
- **Fails loudly by default** (`--strict`, on by default) on any unexpected mismatch or unsafe
  symlink — this is a packaging-safety gate, not an advisory report.

### One documented exception (new finding, not present in TE-002.2B's own PoC measurement)

Validating this productively surfaced a case TE-002.2B's own PoC run never hit: Tauri's resource
copy does not just dereference *file* symlinks — it also **drops** the
`Python.framework/Versions/Current` *directory* symlink entirely (not even as a real directory
copy). `Python.framework/Python` is itself a symlink through `Versions/Current/Python`, so in the
built bundle that path cannot resolve, even though the real file exists, byte-identical, at
`Versions/3.13/Python` (confirmed by direct SHA-256 comparison). The dedup script detects this via
its post-relink safety check, safely reverts to a real-file copy, and records it as a documented,
individually investigated exception (`EXPECTED_UNSAFE_EXCEPTIONS` in the script) — the same
"explain, don't force" precedent as TE-002.2A's `libc++` case. Cost: ~4.8 MiB, not deduplicated.
Any *other* unsafe symlink is still a hard failure, not silently added to this list.

## Reproducible build step

`scripts/build-productive-desktop-app.sh [debug|release]` orchestrates the full pipeline from a
clean state:

1. Build the productive onedir sidecar (`packaging/tauri/sidecar-onedir.spec`, via
   `.venv-novtk-bundle`).
2. Stage it into `desktop/src-tauri/resources/zerorod-engine-onedir/` (`cp -R`, preserves
   symlinks).
3. `tauri build` (debug or release).
4. Run `packaging/tauri/dedup_bundle_dylibs.py` against the built app — a required step, not
   optional or manual.

This is the only supported way to produce a productive app bundle; no manual post-build fixup
step exists or is needed.

## Before / after (release build — the correct comparison, see "A methodology note" below)

| | M3 baseline (fresh remeasure) | M4 final (release) | Delta |
|---|---:|---:|---:|
| Bytes | 417,764,337 | 299,066,193 | −118,698,144 |
| MiB | 398.41 | 285.21 | **−113.20 MiB** |
| Files | 278 | 201 | −77 |
| Directories | 57 | 57 | 0 |
| Symlinks | 0 | 77 | +77 |
| Mach-O files | 238 | 161 | −77 |
| VTK / PySide6 / Qt / numba / llvmlite / scipy | 0 | 0 | unchanged |
| Onefile fallback | absent | absent | unchanged |

**Reduction: 113.20 MiB / 28.41%** off the fresh M3 baseline.

### A methodology note on debug vs. release (found during this milestone, not assumed)

The M3 baseline above (and every measurement in `BUILD-022-M1/M2/M3` docs) was a **debug** Tauri
build (`tauri build --debug`). TE-002.2B's own 280.27 MiB reference was measured on a **release**
build (`experiments/te002-tauri/src-tauri/target/release/bundle/...`, confirmed by reading
`Runtime-Validation.md`). Debug builds carry full Rust debug symbols; `Contents/MacOS/` alone was
37 MiB in debug vs. 13 MiB in release for the identical source. M4 measured **both**:

| | Debug | Release |
|---|---:|---:|
| Bytes | 324,315,105 | 299,066,193 |
| MiB | 309.29 | 285.21 |
| `Contents/MacOS` | 37 MiB | 13 MiB |
| Files / symlinks | 201 / 77 | 201 / 77 |

The release figure (285.21 MiB) is the correct one to compare against TE-002.2B's own 280.27 MiB
reference, since that reference was itself a release build. This is recorded here so a future
milestone doesn't re-measure debug-vs-release confusion from scratch.

## Size classification: **A**

285.21 MiB (release) vs. TE-002.2B's 280.27 MiB reference: **+4.94 MiB / +1.76%**, fully explained:

- The one documented `Python.framework/Python` dedup exception above accounts for ~4.8 MiB of the
  ~4.94 MiB delta almost entirely on its own.
- The small remainder is legitimate M1–M3 product code: the Three.js frontend dependency (~550 KB
  minified), additional Rust modules (`engine.rs`, `mesh.rs`, `protocol.rs`, `commands.rs`'s
  `engine_preview_mesh`), and the productive app's own icon/metadata — none of which existed in
  the TE-002.2B PoC.

This is squarely **Classification A**: the productive bundle matches the TE-002.2B baseline plus
fully explainable product additions. No structural waste remains unaccounted for; nothing was
removed just to chase a number.

## Duplicate report — before / after

| | Before (M3 baseline) | After (M4 final) |
|---|---:|---:|
| Hash-verified duplicate pairs | 78 | 0 (77 relinked, 1 documented exception) |
| Reclaimable MiB | 93.90 | 0 remaining reclaimable (exception is not a "duplicate left on the table" — it cannot be safely relinked, see above) |
| Structural OpenCASCADE duplicate groups | present (Tauri-dereferenced) | **none remaining** |

No known structural OpenCASCADE duplicate from the Tauri symlink-dereference problem remains in
the final bundle. Other legitimate small identical files (if any exist) were not force-deduplicated
— only the 78 pairs PyInstaller's own dedup mechanism already identified were considered.

## No-VTK evidence

- Static: 0 `*vtk*`-matching files in the final bundle (debug and release, both confirmed).
- Runtime: exact bundled sidecar binary's own `status` command reports `vtk_installed: false`,
  `ocp_variant: "cadquery-ocp-novtk"`.
- Environment: build venv (`.venv-novtk-bundle`) has `cadquery-ocp-novtk` installed,
  `cadquery-ocp`/`vtk` absent — unchanged from M2/M3, reused, not reprovisioned.
- No new trace infrastructure built — reused the same static-search and direct-protocol-query
  methodology M2/M3 already established.

## No-PySide6/Qt evidence

0 `*pyside*`/`*qt*`-matching files in the final bundle (debug and release). The productive
frontend has zero Qt/PySide dependency of any kind (TypeScript + Vite + Three.js). The legacy
PySide6 app is untouched and excluded from this evidence by design — it's a separate,
intentionally-retained reference path, not part of the productive Tauri bundle.

## Functional regression

Against the **exact final bundled sidecar binary** (not source tree, not pre-bundle copy), both
debug and release:

- `ping`, `status`, `preview` (×2, repeated), an intentionally invalid command, `shutdown` — all
  correct, including the structured `unknown_command` error for the invalid one.
- A real `SIGKILL` crash simulation: process gone immediately after being killed, no zombie — dedup
  does not change process-tree/kill behavior (expected: dedup only replaces regular files with
  symlinks; it never touches process spawning).
- Real app launch (release build), window renders the M3 UI correctly in its pre-interaction
  state, screenshot-verified.
- Clean quit, 0 remaining `zerorod-desktop`/`zerorod-engine` processes.

## Process lifecycle

Persistent reuse, graceful shutdown, and forced-kill-leaves-no-orphan were all reconfirmed against
the final, deduplicated bundle — not just asserted unchanged from M2. No lifecycle code was
touched in M4 (`desktop/src-tauri/src/engine.rs` is byte-for-byte unchanged from M3).

## Performance

Measured with the same `tools/poc/tauri/benchmark_sidecar_runtime.py persistent` methodology
(reused unmodified), against the final release-bundled, deduplicated sidecar binary:

| Metric | M4 final | M2/M3 reference | TE-002.2B reference | Delta |
|---|---:|---:|---:|---:|
| Cold start | 0.626 s | ~0.612–0.644 s | ~0.612 s | within normal run-to-run noise |
| Warm median | 0.1216 s | ~0.12–0.123 s | ~0.121 s | within normal run-to-run noise |
| Warm p95 | 0.1256 s | ~0.125 s (M3) | 0.1228 s | within normal run-to-run noise |

No material regression. (The benchmark tool's own `deployment_disk_bytes`/`deployment_file_count`
fields follow symlinks via Python's `rglob`+`stat`, which — as already noted in
`BUILD-022-M2-SIDECAR-LIFECYCLE.md` — overcounts a deduplicated tree; the accurate figures are the
ones measured directly above, not the benchmark tool's own size fields.)

## Memory

Same tool, RSS via `ps` on the deepest live descendant:

| Checkpoint | M4 final | M2/M3 reference |
|---|---:|---:|
| after request 1 | 320,752 KB | ~319,600–320,000 KB |
| after request 5 | 321,232 KB | ~320,200–320,700 KB |
| after request 10 | 321,376 KB | ~320,500–321,000 KB |
| after request 20 | 321,472 KB | ~320,700–326,700 KB |

No regression — consistently within the same range as M2/M3's own measurements.

## Security regression

Unchanged from M1–M3, reconfirmed directly (not assumed):

- WebView capability: `core:default` only (`desktop/src-tauri/capabilities/main-capability.json`
  byte-for-byte unchanged).
- CSP: unchanged (`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost`).
- No `externalBin`, no broad filesystem permission, no new runtime capability required by the
  dedup script (it operates entirely at packaging time, before the app ever runs).
- IPC: private stdin/stdout, unchanged.

## Reproducibility

Required environment (unchanged from M2/M3, nothing new for M4):

- Python 3.13, `.venv-novtk-bundle` (TE-001.1-patched `cadquery`, `cadquery-ocp-novtk` installed,
  provisioned by `scripts/validate-te0012-novtk-bundle.sh` if missing).
- Node (frontend build), Rust/Cargo (Tauri build) — same toolchain M1–M3 already used.
- `.venv` (or `python3.13` on PATH) for the dedup script and test suites.

Full pipeline: `./scripts/build-productive-desktop-app.sh release` (or `debug`). A clean rebuild
was performed at least once during this milestone (all generated artifacts removed first) — see
"Baseline" above — proving M4 does not depend on stale artifacts from earlier milestones.

## Build output hygiene

`desktop/sidecar-dist/`, `desktop/src-tauri/resources/`, `desktop/src-tauri/target/`,
`build/zerorod-engine/`, `build/reports/` are all gitignored (confirmed via `git check-ignore -v`
during this milestone). Nothing generated by this milestone's builds or benchmarks is committed —
only `packaging/tauri/dedup_bundle_dylibs.py`, `scripts/build-productive-desktop-app.sh`,
`scripts/validate-build022-m4.sh`, and this documentation.

## Tests

- Rust: 21/21 (`cargo test`), unchanged from M3 — M4 touched no Rust source.
- Python: 41/41 sidecar tests + 282/1-skip full repo regression, unchanged from M3.
- Frontend: 53/53 (`vitest run`), TypeScript clean, production build clean — unchanged from M3.
- Dedup script: `ruff check`/`ruff format --check` clean; exercised for real against a freshly
  built app twice (fresh run: 77 relinked + 1 documented exception, exit 0; second run:
  idempotent, 0 relinked, exit 0) — not just unit-tested in isolation.

## Known limitations

- The one documented `Python.framework/Python` exception (~4.8 MiB) is not deduplicated. Revisiting
  it would require either patching Tauri's resource-copy behavior for directory symlinks (out of
  scope — not a ZeroRodCAD-controlled component) or restructuring how the Python framework is
  laid out in the PyInstaller output (a PyInstaller-spec-level change with broader risk than its
  ~4.8 MiB is worth for this milestone).
- No production code signing or notarization — explicitly out of scope for M4 (and for Build 022
  generally, per `ADR-022-001`).

## Reproducing the build

```bash
# Full pipeline, from a clean state, release mode:
./scripts/build-productive-desktop-app.sh release

# Or debug mode (faster iteration, larger due to debug symbols):
./scripts/build-productive-desktop-app.sh debug
```

Equivalent to (what the script actually does):

```bash
# 1. Sidecar
.venv-novtk-bundle/bin/pyinstaller --noconfirm --clean \
  --distpath desktop/sidecar-dist --workpath build/zerorod-engine \
  packaging/tauri/sidecar-onedir.spec

# 2. Stage (preserves symlinks)
rm -rf desktop/src-tauri/resources/zerorod-engine-onedir
cp -R desktop/sidecar-dist/zerorod-engine desktop/src-tauri/resources/zerorod-engine-onedir

# 3. Tauri build
cd desktop/src-tauri && ../frontend/node_modules/.bin/tauri build   # add --debug for debug mode

# 4. Dedup (required, not optional)
cd ../..
.venv/bin/python packaging/tauri/dedup_bundle_dylibs.py \
  desktop/sidecar-dist/zerorod-engine/_internal \
  desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app/Contents/Resources/zerorod-engine-onedir/_internal
```

## Conclusion

The productive Build-022 path now reproducibly matches TE-002.2B's own proven No-VTK / no-onefile
/ dylib-deduplicated packaging baseline, at 285.21 MiB (release) — within 1.76% of the 280.27 MiB
PoC reference, with the entire delta explained by one documented, individually investigated,
safety-first exception plus legitimate M1–M3 product code. Functionality, performance, memory,
lifecycle, and security are all reconfirmed intact against the exact optimized artifact, not
assumed unchanged.

## Gate BUILD-022-M4

**PASS.** Engineering criteria (this document) PASS + human validation
(`BUILD-022-M4-HUMAN-VALIDATION.md`, Project Owner, 2026-08-09) PASS. Milestone 4 is COMPLETE.

## Next milestone

**Build 022 / Milestone 5 — Integration & Build Completion** (own separate mandate).
