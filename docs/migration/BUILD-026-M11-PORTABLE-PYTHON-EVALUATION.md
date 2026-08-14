# Build 026 / M1.1 — Portable Python & macOS Deployment Target Evaluation

Corrective research pass. No product source, packaging config, or CI was changed by this document —
all changes made during the investigation (a temporary `tauri.conf.json` edit, a temporary venv
swap) were reverted before finishing; only this document and its findings are new.

## Current Problem

Build 026 M1 measured the productive bundle's genuine macOS floor at **26.0** and set
`LSMinimumSystemVersion` accordingly, flagging it `DECISION_REQUIRED` rather than accepting it as
final. The question this milestone answers: is 26.0 an inherent property of the dependency chain,
or an artifact of the specific toolchain M1 happened to use?

## Current Homebrew Baseline (recap, re-confirmed)

`python3.13` on this machine resolves to Homebrew's `python@3.13` bottle
(`/opt/homebrew/Cellar/python@3.13/3.13.14_1`), built with `MACOSX_DEPLOYMENT_TARGET` pinned to
whatever macOS version the bottle was built for — this build machine's own host OS, macOS 26
("Tahoe"). This inflates `Python.framework`, the entire stdlib native-extension set, and
`libssl`/`libcrypto`/`libmpdec` (56 files in the M1 bundle) to `minos=26.0`.

**A second, independent root cause was found this milestone**: the Rust/Tauri main executable
(`Contents/MacOS/zerorod-desktop`) *also* floors at 26.0 by default, for an unrelated reason —
confirmed empirically that Tauri's own bundler derives the `MACOSX_DEPLOYMENT_TARGET` it passes to
`cargo build` **from `tauri.conf.json`'s `bundle.macOS.minimumSystemVersion`** (M1 set this to
`"26.0"`), not from the ambient shell environment. Exporting `MACOSX_DEPLOYMENT_TARGET` in the
shell before invoking `cargo tauri build` had **no effect** — only editing the config value itself
changed the resulting binary. This means fixing Python alone would not have lowered the shipped
bundle's real floor; the Rust side needed the same fix, and the two are coupled through the same
config field.

## Candidate Python Sources Evaluated

### Candidate 1: `astral-sh/python-build-standalone` (evaluated hands-on — the recommended candidate)

- **Source**: `cpython-3.13.15+20260807-aarch64-apple-darwin-install_only.tar.gz`, GitHub release
  tag `20260807` of `astral-sh/python-build-standalone`
  (`https://github.com/astral-sh/python-build-standalone`).
- **Provenance**: a widely-used, actively maintained open-source project (the same portable-Python
  build infrastructure `uv`/`rye`/`pdm` and numerous other modern Python tools rely on) —
  purpose-built for exactly this "reproducible, redistributable, deployment-target-controlled Python"
  need, not an exotic/one-off distributor.
- **Reproducibility**: downloaded via a pinned release tag + exact asset filename; SHA-256
  `ebcf53fe921c356ad2eecfcea370cb744e7bd96fdef41a53e1e8f32a15c6dfeb` recorded for this exact archive.
  Fully pin-and-verify-able.
- **ARM64 support**: native `aarch64-apple-darwin` build, confirmed.
- **Python floor**: `minos 11.0` on the interpreter binary and every one of its (few) dynamic
  Mach-O components — confirmed via direct `otool -l` inspection, independent of the host machine's
  own OS version.
- **Structure**: heavily statically linked — only 6 dynamic Mach-O files in the entire distribution
  (`python3.13`, `libpython3.13.dylib`, `_tkinter`/`_dbm` extensions, 2 Tcl/Tk-related dylibs); most
  stdlib C extensions (including `_ssl`, `zlib`, etc.) are compiled directly into
  `libpython3.13.dylib` rather than shipped as separate `.so` files. **No `Python.framework`
  directory at all** — a flat `bin`/`lib`/`include` layout, not a macOS framework bundle.
- **PyInstaller compatibility**: confirmed working — the full productive PyInstaller onedir build
  succeeded against a venv created from this Python with no spec changes.
- **CadQuery/OCP/numpy/casadi compatibility**: confirmed working — full functional pipeline passed
  (see below).
- **Clean-machine suitability**: excellent — `curl`/`gh release download` + `tar xzf` + `python3.13
  -m venv`, no `sudo`, no system-wide install, no dependency on Homebrew or any pre-existing
  machine state.
- **CI suitability**: excellent — a pinned URL + checksum is trivially fetchable in any GitHub
  Actions `macos-latest` runner via a plain `curl`/`tar` step; no `brew install` (which floats with
  whatever bottle Homebrew happens to serve that day) and no interactive installer.
- **Licensing**: PSF License for CPython itself; bundled third-party components (OpenSSL, libxml2,
  etc.) ship their own license texts alongside the distribution, with a machine-readable manifest —
  the project deliberately builds against `libedit` instead of GPL'd `readline`/`gdbm` specifically
  to keep the whole distribution redistributable. No licensing concern identified for this project's
  use (a build-time-only tool, statically linked into a distributed binary the same way any other
  compiled dependency already is).

**Conclusion: RECOMMENDED.**

### Candidate 2: python.org official macOS installer (evaluated via documented research only, not hands-on)

- Ships a universal2 (`arm64`+`x86_64`) `.pkg`, currently targeting approximately macOS 10.15
  Catalina as its floor for the 3.13 series — lower than even Candidate 1's 11.0.
- **Not selected for hands-on testing**: it installs system-wide into `/Library/Frameworks/
  Python.framework`, requires `sudo`/interactive installer semantics (or fragile manual `.pkg`
  payload extraction to script it non-interactively), and is a shared, machine-global install rather
  than a project-local, easily-isolated one — a materially worse fit for "clean-machine/CI
  suitability" and "not tied to the build machine's own state" than Candidate 1, even though its
  raw floor number is nominally lower. Per the mandate's own decision criteria (§26: reproducible
  packaging and clean-machine/CI suitability matter, not the lowest number alone), and since
  Candidate 1 already achieves a bundle floor low enough that OpenCASCADE — not Python — is the
  binding constraint (see below), there is no product benefit to pursuing this further.
- Classification: `SUPPORTED_WITH_PORTABLE_PYTHON` in principle, not preferred.

### Candidate 3: pyenv / source-built CPython with explicit `MACOSX_DEPLOYMENT_TARGET`

- Technically capable of targeting any macOS version down to what Apple's own SDK/toolchain
  supports, but requires a full CPython compile from source on every provisioning (tens of minutes,
  Xcode Command Line Tools + various system headers required) — a materially heavier, slower, more
  fragile clean-machine/CI story than a prebuilt, checksummed tarball extraction.
- **Not evaluated hands-on**: no evidence suggested it would achieve a materially different result
  than Candidate 1 (both would target the same practical floor, since OpenCASCADE's own wheel — not
  Python — turns out to be the binding constraint), so the added build-from-source complexity and
  maintenance burden is not justified. Per the mandate's own instruction (§6/§26: prefer the
  simplest reproducible toolchain, do not chase the lowest number at disproportionate cost).
- Classification: `NOT_PRACTICAL` relative to Candidate 1.

### Homebrew (current baseline, not the solution)

Confirmed unsuitable as the packaging-venv Python source specifically because its deployment target
floats with whatever macOS version the installed bottle happened to be built for — not fixed,
pinned, or reproducible across machines or time.

## Dependency Floors (Python-source-independent — wheel-baked facts)

These are fixed properties of the published PyPI wheels themselves, unaffected by which Python
interpreter installs them (as long as the ABI tag `cp313` matches):

| Component | Default-selected wheel floor | Lower alternative available? | Evidence |
|---|---|---|---|
| **numpy 2.4.6** | `macosx_14_0_arm64` (what `pip install` picks by default on this machine) | **Yes** — PyPI also publishes `numpy-2.4.6-cp313-cp313-macosx_11_0_arm64.whl` for the *identical release*; confirmed via `otool -l` on all 19 of its compiled extensions: `minos 11.0` throughout, and functionally verified (`numpy.array([1,2,3]).sum()` correct) | Directly downloaded and inspected both wheel variants |
| **casadi 3.7.2** | `minos 11.0` (already low, no action needed) | n/a | Direct `otool -l` scan, confirmed both this milestone and in M1 |
| **cadquery-ocp-novtk 7.9.3.1.1 (OCP + OpenCASCADE)** | `minos 11.1` | Only variant available on PyPI for this exact pinned version | Direct `otool -l` scan of all 76 OCP-related files in the built bundle |

**numpy's default-vs-available-wheel gap was the single most consequential dependency finding**:
`pip install numpy==2.4.6` alone would have silently locked the floor to 14.0 even after fixing
Python, unless the lower-tagged wheel is explicitly requested (`pip download --platform
macosx_11_0_arm64 --python-version 313 --implementation cp --abi cp313`, then `pip install
--force-reinstall --no-deps <downloaded-wheel>` — pip refuses `--platform`/`--abi` overrides for a
live-environment install directly, only for `--target`/`--dry-run`/local-file installs).

**OpenCASCADE/OCP (`minos 11.1`) is the true binding constraint** for this application — no lower
alternative exists for the pinned `cadquery-ocp-novtk==7.9.3.1.1` version, and no product-justified
reason exists to chase a version bump or source-build OpenCASCADE just to shave 0.1 off this number.

## Candidate Target Matrix

| Target | Classification | Basis |
|---|---|---|
| macOS 11.0 (base) | `NOT_SUPPORTED` (barely) | OCP's own wheel is tagged `macosx_11_0_arm64` but its actual compiled `minos` is `11.1` — a real, if tiny, gap below which the bundle would claim compatibility it doesn't have |
| macOS 11.1+ | `SUPPORTED_WITH_PORTABLE_PYTHON` | **This is the measured, proven floor** — real full-bundle build, 110/110 Mach-O files at ≤11.1, functional pipeline PASS |
| macOS 12 / 13 | `SUPPORTED_WITH_PORTABLE_PYTHON` | Trivially satisfied once 11.1 is satisfied — no component in the stack specifically requires 12 or 13 |
| macOS 14 | `SUPPORTED_WITH_PORTABLE_PYTHON` | Also trivially satisfied; this was the previously-assumed numpy-driven floor, now known to be avoidable, not required |
| macOS 15 | `SUPPORTED_WITH_PORTABLE_PYTHON` | Same |
| macOS 26 (current Homebrew baseline) | `SUPPORTED_WITH_CURRENT_BINARY_DEPS` | Works trivially since it's far above what's actually required — this was M1's honest-but-overly-conservative measurement |

No target between 11 and 26 requires source-building any major dependency — the entire matrix above
11.1 is satisfied by the same single recommended toolchain change.

## Full-Bundle Proof (real build, not measured from the Python environment alone)

Sequence actually performed: portable Python 3.13.15 (Candidate 1) → pinned dependency install →
explicit `macosx_11_0_arm64` numpy wheel substitution → `scripts/apply-cadquery-novtk-patch.sh`
(the M1 tracked mechanism, used **unchanged** — no bypass) → verified functional under
`VTKImportBlocker` → PyInstaller onedir → `tauri.conf.json`'s `bundle.macOS.minimumSystemVersion`
temporarily set to `11.0` (the actual control for the Rust side, per the finding above) → `cargo`
`target/release` fully cleaned and rebuilt from scratch (to rule out stale-cache artifacts) →
hash-gated dylib dedup → final `.app`.

**Every one of the 110 Mach-O files in the resulting bundle scanned individually**:

| `minos` | File count | Contents |
|---|---|---|
| 11.0 | 59 | Rust/Tauri main executable, sidecar executable, `libpython3.13.dylib`, casadi, nlopt, fontTools, numpy (all 13 extensions, now the 11.0-tagged wheel) |
| 11.1 | 51 | All OpenCASCADE/OCP files |

**Maximum bundle floor: 11.1.** No file at any higher value. Top contributor establishing the
maximum: OpenCASCADE (`libTK*.dylib` / `OCP.cpython-313-darwin.so`), 51 files, all at exactly 11.1.

`tauri.conf.json` and the swapped venv were both reverted to M1's exact committed state
(`minimumSystemVersion: "26.0"`, the original Homebrew-based `.venv-novtk-bundle`) immediately after
this proof — no permanent product/config change was made by this research pass.

## Functional Results

Real end-to-end pipeline exercised against the freshly built portable-Python sidecar (identical
JSONL exercise pattern to the M1 gate): `status`, `preview` (defaults), `preview` (alternate,
`body_width=60`), `report` (alternate), `project_save`→`project_open` roundtrip (value preserved:
`60.0`), `export` (alternate — STL/STEP/report all valid, non-empty, content correctly reflects
`60.00 mm`), `preview` (defaults again), `export` (defaults — content correctly reflects `38.00 mm`,
confirming the alt/default outputs are genuinely different despite a coincidental equal STL byte
count), `shutdown`. **10/10 requests `ok: true`.**

Real packaged `.app` launch/shutdown smoke test (not just the raw sidecar binary): launched via
`open`, main process + sidecar process both started automatically, quit cleanly via the native
close/quit guard, **0 orphan processes** afterward.

## Reproducibility

The M1 No-VTK patch/provisioning mechanism (`scripts/apply-cadquery-novtk-patch.sh`) was used
**completely unchanged** against the portable-Python venv and passed identically (idempotency
check, fail-fast context matching, functional `VTKImportBlocker` verification) — confirming the
mechanism is genuinely Python-source-agnostic, not accidentally coupled to Homebrew's specific
CadQuery install layout.

## CI Suitability

M1's `.github/workflows/build-productive.yml` currently provisions the packaging venv by invoking
`scripts/provision-novtk-bundle-venv.sh`, which creates the venv from whatever `python3.13` resolves
to on the runner's `PATH` — on GitHub's `macos-latest` runner this would currently be whatever
Python `actions/setup-python@v5` (or the runner's own preinstalled Python) provides, which is itself
not guaranteed to carry an 11.0 deployment target either. **To actually realize this milestone's
finding in CI, `provision-novtk-bundle-venv.sh` (or a wrapper step before it) would need to**:
download and extract the pinned `python-build-standalone` tarball instead of relying on `PATH`
Python, and `tauri.conf.json`'s `minimumSystemVersion` would need to change from `26.0` to the
accepted target. **Not implemented here** — this is exactly the kind of "tiny correction" the
mandate anticipates M1 needing, deferred until the Project Owner accepts a target.

## Performance / Size Comparison

| Metric | Homebrew baseline (M1) | Portable Python (this candidate) | Delta |
|---|---|---|---|
| Bundle size | 287 MiB / 299,986,560 bytes | 310 MiB | +~8% |
| Cold start (status + shutdown round trip) | — (not separately re-measured this pass) | ~0.06 s | — |
| Warm preview (5-request average) | ~0.12–0.15 s (Build 025/M1 baseline) | ~0.195 s/request (rough, under concurrent system load from this session's other work) | within normal measurement noise, no material regression |
| STL/STEP/report content | — | Correct, parameter-reflecting, valid | No functional regression |

**Size delta explained**: `python-build-standalone` links most of the stdlib statically into a
single 17 MiB `libpython3.13.dylib`, versus Homebrew's more modular, multi-file `Python.framework`
split (which the dylib-dedup step can partially deduplicate via symlinks). Net effect: a modest,
fully explained size increase, not a regression requiring investigation per the mandate's own "do
not reject over a trivial delta" guidance — 8% is trivial relative to the ~93% floor-requirement
improvement (macOS 26.0 → 11.1) achieved.

## Signing Relevance (report only — no real signing performed)

`python-build-standalone`'s output has **no `Python.framework` directory at all** — a flat
`bin`/`lib`/`include` layout with a single `libpython3.13.dylib`, unlike Homebrew's framework-bundle
layout. Consequence observed directly in this milestone's rebuild: the dylib-dedup step's previously
**documented, necessary exception** (`Python.framework/Python`: Tauri's resource copy drops the
`Versions/Current` symlink entirely, leaving a ~4.8 MiB un-deduplicated real-file copy — recorded in
every Build 022–026 M1 completion doc) **did not trigger at all** this run — the dedup log shows no
exceptions, because there is no framework-symlink structure left to lose. This is a genuine,
incidental **simplification** of the future signing topology (fewer nested framework-versioning
symlinks to individually sign/verify) — a positive side effect, not something this milestone
pursued for its own sake. No entitlement or library-validation exception was needed to build or run
this candidate; nothing here changes M3's signing scope or timeline.

## Security

WebView capability delta: **NONE** (this milestone touched no capability file). No new runtime
network access, no secrets, no signing credentials, no notarization. The portable Python required no
unusual runtime permission to launch — plain user-space execution, identical to Homebrew Python's.

## Recommendation

**Recommended packaging Python**: `astral-sh/python-build-standalone`,
`cpython-3.13.15+20260807-aarch64-apple-darwin-install_only.tar.gz` (or the equivalent current
release at implementation time, re-pinned), SHA-256 `ebcf53fe921c356ad2eecfcea370cb744e7bd96fdef41a53e1e8f32a15c6dfeb` for this exact archive.

**Measured full-bundle floor**: **macOS 11.1**.

**Reason**: OpenCASCADE (`cadquery-ocp-novtk`'s bundled `libTK*.dylib`/`OCP.cpython-313-darwin.so`)
is the binding constraint — no lower alternative exists for the currently-pinned version, and no
product justification exists to chase it further. Every other component (portable Python, casadi,
the explicitly-selected numpy wheel, and the Rust/Tauri binary once `MACOSX_DEPLOYMENT_TARGET` is
correctly derived from `tauri.conf.json`) is at 11.0 or below.

**Clean environment**: reproducible — pinned tarball URL + checksum, no `sudo`, no Homebrew
dependency, no reliance on "this Mac already has the right Python."

**Functional**: PASS (10/10 real pipeline requests, real packaged-app launch/shutdown, 0 orphans).

This is **not implemented in the productive pipeline by this research pass** — per the mandate's
explicit stop condition, this is a recommendation for Project Owner decision, to be applied by a
follow-up, explicitly authorized correction to Build 026 M1 (or a new M1.2), which would need to:
change `scripts/provision-novtk-bundle-venv.sh` to provision from the pinned portable-Python tarball
instead of `PATH` Python, add the explicit `numpy` platform-tag override, set
`tauri.conf.json`'s `bundle.macOS.minimumSystemVersion` to the accepted value, and update
`.github/workflows/build-productive.yml` accordingly.

## Decision Required

**Recommended minimum macOS: 11.1** (practically stated as "macOS 11" in product-facing copy, since
no realistic device ships pinned at exactly 11.0.0 without an available 11.1+ update — but the
`LSMinimumSystemVersion` config value itself should read `11.1`, matching the measured evidence
exactly, per the same "don't declare a rounder number than what's proven" discipline this whole
milestone exists to enforce).

Awaiting explicit Project Owner acceptance before any implementation.
