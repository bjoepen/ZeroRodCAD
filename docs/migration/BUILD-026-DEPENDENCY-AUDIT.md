# Build 026 — Dependency Audit

Discovery document. No dependency was upgraded, pinned, patched, installed, or removed to produce
this audit. All findings are against the current-HEAD Build 025 final `.app` bundle and the
repository's tracked dependency/lockfile/bootstrap-script state, gathered read-only.

## Dependency Inventory (against the actual final `.app` bundle)

| Component | Version | On-disk size | Why required |
|---|---|---|---|
| Python runtime | 3.13 (`Python.framework/Versions/3.13`) | ~9.6 MiB (framework itself) | Sidecar interpreter |
| CadQuery | 2.8.0 | 48 KiB dist-info | Core CAD API `zerorodcad` builds on |
| cadquery-ocp-novtk | 7.9.3.1.1 | 72 KiB dist-info + OCP payload | The No-VTK OCP wrapper — TE-001/TE-001.1's decision |
| numpy | 2.4.6 | 260 KiB dist-info | CadQuery/OCP numeric dependency |
| casadi | 3.7.2 | ~15 MiB (`_casadi.so` + payload) | **Transitive dependency of `cadquery` itself** (`pip show casadi` → `Required-by: cadquery`); not directly imported by `zerorodcad`/`zerorod_sidecar` source (0 grep hits) — CadQuery uses it internally |
| OpenCASCADE (`libTK*.dylib`) | 7.9.3 | 50 distinct filenames, ~64.5 MiB unique content (rest are dedup symlinks) | OCP's underlying C++ geometry kernel |
| Tauri (Rust crate) | 2.11.5 (`Cargo.lock`) | n/a (compiled into main executable) | Desktop shell framework |
| Three.js | resolved via `package-lock.json` from `"^0.185.1"` | n/a (compiled into frontend bundle) | Preview renderer |
| PyInstaller (build tool, not shipped) | 6.21.0 (in `.venv-novtk-bundle`) | n/a | Packaging tool only |

Dependency-exclusion invariants, re-confirmed directly against the bundle:

| Dependency | Count |
|---|---|
| VTK | 0 (the one raw filename hit is the established `cadquery_ocp_novtk-*.dist-info` substring false positive) |
| PySide6 | 0 |
| Qt | 0 |
| numba | 0 |
| llvmlite | 0 |
| scipy | 0 |

All clean, matching Build 025's own final measurement.

## PyInstaller Hidden-Import Warning Investigation

The build log's two warnings did not break the build (exit 0) but were investigated for root cause
rather than dismissed:

### `cadquery.exporters` — **OBSOLETE_HIDDEN_IMPORT**

`cadquery/__init__.py` does `from .occ_impl import exporters`, which makes `cadquery.exporters` a
valid *runtime attribute* (and is exactly what `zerorodcad/export.py:37` uses:
`from cadquery import exporters`) — but the real importable *module path* PyInstaller's
hiddenimports mechanism needs is `cadquery.occ_impl.exporters`, not `cadquery.exporters`.
`"cadquery.exporters"` as a literal hiddenimport string can never resolve, because no file exists at
that path (confirmed: `find .venv-novtk-bundle -path "*cadquery/exporters*"` finds nothing there;
the real file is under `cadquery/occ_impl/exporters/`). Since `cadquery` (the package) is already
collected, PyInstaller's static module-graph analysis of `cadquery/__init__.py`'s own `from
.occ_impl import exporters` statement collects the real submodule automatically — the explicit
hiddenimport was never actually needed. STL/STEP export is proven working end to end in the shipped
Build 025 app (established previously, not re-verified here), consistent with this explanation:
the warning is cosmetic, not a sign of missing functionality.

### `OCP.TKernel` — **OBSOLETE_HIDDEN_IMPORT**

`OCP/__init__.py` is `from OCP.OCP import *` (plus `__version__`) — the entire OCP binding is one
compiled extension (`OCP.cpython-313-darwin.so`). pybind11 registers several of its internal
namespaces as fake `sys.modules` entries, so `import OCP.BRep` / `OCP.BRepMesh` /
`OCP.STEPControl` / `OCP.StlAPI` all succeed — but `OCP.TKernel` does not:
`import OCP.TKernel` raises `ModuleNotFoundError: No module named 'OCP.TKernel'`, confirmed live
against the exact `.venv-novtk-bundle` used for packaging. A repo-wide grep for `OCP.TKernel` shows
it referenced **only** in the two `.spec` files (`packaging/macos/ZeroRodCAD.spec` — the legacy
PySide6 spec — and `packaging/tauri/sidecar-onedir.spec`) and nowhere in productive ZeroRodCAD
source — strong evidence it was copy-pasted from the legacy spec into the Tauri spec without
verification. The native `libTKernel.7.9.3.dylib` toolkit **is** correctly bundled (PyInstaller
discovers it via binary/`otool`-level analysis of the OCP extension's actual linked libraries, not
via this Python-level hiddenimport) — so, again, nothing is actually missing; the declaration is
simply wrong and inert.

**Recommended action** (for a later, explicitly authorized implementation milestone, not this
discovery pass): remove both entries from `packaging/tauri/sidecar-onedir.spec`'s `hiddenimports`
list, with a before/after regression proof (a real rebuild plus preview + STL + STEP export against
the rebuilt bundle) to confirm removing the dead declarations changes nothing. Not implemented here.

## Lockfile / Pin Audit

- **`desktop/src-tauri/Cargo.lock`**: git-tracked, all dependencies resolve from
  `registry+https://github.com/rust-lang/crates.io-index` — 0 git/path (non-registry) sources.
  Fully reproducible via `cargo build --locked`.
- **`desktop/frontend/package-lock.json`**: git-tracked, npm format. Reproducible via `npm ci`
  despite `package.json` itself using caret ranges (e.g. `"three": "^0.185.1"`) — the committed
  lockfile pins the exact resolved version.
- **Python build-venv provisioning** (`scripts/validate-te0012-novtk-bundle.sh`, the script that
  actually provisions `.venv-novtk-bundle`): pins are **mixed and largely loose**:
  - `cadquery-ocp-novtk==7.9.3.1.1` — exact.
  - `cadquery==2.8.0 --no-deps` — exact.
  - `ezdxf>=1.3.0`, `multimethod<2.0,>=1.11`, `nlopt<3.0,>=2.9.0`, `pyparsing>=3.0.0` — range-pinned.
  - `runtype`, `casadi`, `scipy`, `numba` — **completely unpinned** (bare package name, any
    version). `scipy`/`numba` are excluded from the final bundle by the PyInstaller spec regardless
    (confirmed 0 above), but they're still installed unpinned into the *build* venv, and `casadi`'s
    actual bundled version (3.7.2) is whatever PyPI resolves at install time — not a pin, even
    though it ships in the product.
  - `PySide6>=6.7,<7`, `PyInstaller>=6.16,<7` — range-pinned (PyInstaller resolved to 6.21.0).
  - No `pyproject.toml`/`requirements*.txt` governs this venv — the pins above exist only as
    literal `pip install` arguments inline in the bootstrap script.

## Build Environment / Toolchain Reproducibility

| Tool | Pin mechanism |
|---|---|
| macOS | Prose-documented only, no enforcement |
| Xcode/CLT | Not checked/pinned anywhere found |
| Rust/Cargo | `Cargo.toml` sets `edition = "2021"` only — no `rust-toolchain.toml` |
| Node | No `.nvmrc`, no `engines` field in `package.json` |
| npm | Implied by `package-lock.json` presence; no version pin |
| **Python** | `scripts/validate-te0012-novtk-bundle.sh` asserts `python3.13` on PATH and checks `sys.version_info[:2] == (3,13)` — an **enforced check**, the strongest pin found anywhere in the toolchain |
| PyInstaller | Range-pinned only (`>=6.16,<7`) |
| Tauri CLI | Not independently pinned as a CLI tool (only the Rust crate is pinned via `Cargo.lock`) |

Only the Python major.minor version is actually enforced; everything else is, at best,
prose-documented with no enforcement mechanism.

## Clean-Machine Build Question — the critical finding

**The productive pipeline does not currently bootstrap cleanly from a fresh clone.** Traced through
the actual script chain:

1. `scripts/build-productive-desktop-app.sh` hard-requires `.venv-novtk-bundle` to already exist
   and exits with an instruction to run `scripts/validate-te0012-novtk-bundle.sh` first — it
   provisions nothing itself.
2. `scripts/validate-te0012-novtk-bundle.sh` **does** create `.venv-novtk-bundle` and install the
   dependency list above — but its install block is gated by `if ! python -c "import cadquery"`,
   so it **silently no-ops on any pre-existing venv**, even a stale one with drifted unpinned
   versions. This script is otherwise a **legacy TE-001.2 PySide6-app validation script** (it builds
   `packaging/macos/ZeroRodCAD.spec` → `dist/ZeroRodCAD Desktop.app` and runs a PySide6
   `--startup-test`) being reused only for the side effect of provisioning the shared venv — a
   non-obvious, indirect provisioning path for the productive Tauri sidecar.
3. Critically, its own "apply the TE-001.1 patch" step does not apply a patch at all — it **copies
   4 already-patched files** (`occ_impl/shapes.py`, `occ_impl/exporters/vtk.py`,
   `occ_impl/assembly.py`, `occ_impl/exporters/assembly.py`) out of a **separate venv**,
   `.venv-novtk-poc`, and fails with an explicit error if that venv doesn't exist.
4. `scripts/validate-te001-novtk.sh` creates `.venv-novtk-poc` — but installs **vanilla, unpatched**
   `cadquery==2.8.0`. **No tracked script anywhere in the repository actually applies the
   VTK-import-removal patch to `.venv-novtk-poc`.** A repo-wide grep for patch-application logic
   (`patch -p`, `git apply`, references to the diff filenames under
   `docs/research/TE-001.1-CadQuery-NoVTK/patches/`) returns zero hits. Those four `.diff` files are
   diffs generated *from* an already-hand-patched `.venv-novtk-poc` against a scratchpad copy of the
   originals (their own diff headers reference a session-specific temp path) — a **historical
   record of what changed, not a script anyone or anything applies**. `.venv-novtk-poc` exists on
   this machine right now with a working patched CadQuery install, but its provenance is not
   reproduced by any tracked repository script.

### Classification

- **repository-reproducible**: Cargo build (`cargo build --locked`), frontend build (`npm ci`), the
  exact-pinned half of Python deps (`cadquery`, `cadquery-ocp-novtk`), the Python-3.13 enforcement
  check.
- **machine-local prerequisite** (something must be present on the machine, no secret): `python3.13`
  on PATH, Xcode/CLT (implied, unverified), Rust toolchain, Node/npm — all standard macOS
  developer-machine setup, none blocking.
- **secret prerequisite**: none currently (only future signing/notarization credentials, per the
  signing analysis).
- **REQUIRED_FOR_DISTRIBUTION — outside all three buckets above**: the CadQuery No-VTK patch's
  actual application to `.venv-novtk-poc` is **undocumented, unscripted local state**. A fresh clone
  run through `scripts/validate-te001-novtk.sh` → `scripts/validate-te0012-novtk-bundle.sh` →
  `scripts/build-productive-desktop-app.sh` in sequence would **not** reproduce the currently-
  shipping, patched, No-VTK bundle — it would either fail outright (patch source venv missing) or,
  worse, silently produce an **unpatched, VTK-importing sidecar** if the `import cadquery`-succeeds
  skip-gate in step 2 masked the problem on a machine where some *other* cadquery install
  happened to already satisfy that gate. This is the single most important reproducibility finding
  of this audit, and per the ADR's own instruction ("every migration build that touches packaging or
  dependency versions must keep this patch's applicability visible… not assume it stays applied by
  accident") it should be closed — with a tracked, scripted, reproducible patch-application step —
  before Build 026 treats the packaging pipeline as production-trustworthy. Not fixed in this
  discovery pass; flagged for the milestone plan.

## CI

`.github/workflows/tests.yml` runs `pytest`/`ruff` against the Python package on `macos-latest` plus
a `pre-commit` job on `ubuntu-latest`. It does **not** build or test the Rust/Tauri app, the
frontend, the PyInstaller sidecar, or the productive packaging pipeline at all — so there is
currently **zero independent CI evidence** of clean-machine reproducibility for anything covered by
`scripts/build-productive-desktop-app.sh`. This corroborates rather than contradicts the gap above:
if CI had actually been exercising this pipeline on a clean runner, the patch-provenance gap would
likely already have surfaced as a build failure.

## Summary Classification

| Area | Status |
|---|---|
| Dependency-exclusion invariants (VTK/PySide6/Qt/numba/llvmlite/scipy) | ALREADY_COMPLETE |
| Cargo.lock / package-lock.json pinning | ALREADY_COMPLETE |
| Python exact-pin coverage (cadquery, cadquery-ocp-novtk) | ALREADY_COMPLETE |
| Python loose-pin coverage (casadi, runtype, scipy, numba in build venv) | RECOMMENDED_HARDENING |
| Toolchain pin files (Rust/Node) | RECOMMENDED_HARDENING |
| PyInstaller hidden-import warnings | OBSOLETE_HIDDEN_IMPORT (both) — RECOMMENDED_HARDENING to remove |
| CadQuery No-VTK patch clean-machine reproducibility | **REQUIRED_FOR_DISTRIBUTION** |
| CI coverage of the productive packaging pipeline | REQUIRED_FOR_DISTRIBUTION (Stage 1, see release-workflow analysis) |
