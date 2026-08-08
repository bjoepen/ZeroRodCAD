# TE-001 — Dependency Governance

Every dependency newly considered or installed for TE-001, evaluated against the governance
checklist (section 4 of the mandate) before installation. TE-001 introduced exactly one new
third-party dependency (`cadquery-ocp-novtk`); everything else used already-vendored ZeroRodCAD
code or the Python standard library.

## `cadquery-ocp-novtk`

- **Version**: 7.9.3.1.1
- **Purpose**: VTK-free build of the OCP (Open CASCADE Python) bindings CadQuery depends on — the
  entire subject of this evaluation.
- **Source**: PyPI, https://pypi.org/project/cadquery-ocp-novtk/
- **Maintenance status**: active. Maintainers `b_walter` (Bernhard Walter) and `jmwright` — the
  same team that maintains upstream CadQuery and `cadquery-ocp`.
- **Last stable release**: 7.9.3.1.1, 2026-05-28 (verified live via PyPI JSON API).
- **Release history** (verified): 7.7.2.2b2 (2024-12-23) → 7.8.1.0 (2025-01-13) → 7.8.1.1
  (2025-01-22) → 7.8.1.1.post1 (2025-01-29) → 7.9.3.0 (2026-01-03) → 7.9.3.1 (2026-02-15) →
  7.9.3.1.1 (2026-05-28). Regular cadence, no gap suggesting abandonment.
- **Python 3.13 compatibility**: confirmed — `cadquery_ocp_novtk-7.9.3.1.1-cp313-cp313-*` wheels
  exist for macOS (both arm64 and x86_64), manylinux (aarch64 and x86_64), and Windows. cp314
  wheels also exist (ahead of ZeroRodCAD's own `>=3.13,<3.14` requirement, no concern).
- **macOS ARM64 compatibility**: confirmed —
  `cadquery_ocp_novtk-7.9.3.1.1-cp313-cp313-macosx_11_0_arm64.whl` verified present in the PyPI
  file listing and successfully installed/imported in TE-001 (`Experiment.md`, `Results.md`).
- **Deprecation/security/abandonment signals**: none found.
- **License**: Apache-2.0.
- **Alternative considered**: `cadquery-ocp` (the VTK-bundling variant) — rejected, since bundling
  VTK is exactly what this evaluation tests removing. No other actively-maintained VTK-free OCCT
  Python binding compatible with CadQuery's expected `OCP` import surface was found.
- **Decision**: use, pinned to `7.9.3.1.1` for reproducibility of this evaluation.

## `cadquery-ocp-proxy` (transitive, pulled in automatically by `cadquery-ocp-novtk`)

- **Version**: 7.9.3.1.1 (pinned by `cadquery-ocp-novtk`'s own `requires_dist`).
- **Purpose**: version-tracking proxy package; declares no required dependencies of its own,
  exists so `cadquery-ocp`/`cadquery-ocp-novtk` releases stay in lockstep.
- **Source**: PyPI, same maintainers as above.
- **Maintenance status**: active, same release cadence as `cadquery-ocp-novtk`.
- **Python 3.13 / macOS ARM64 compatibility**: `py3-none-any` — platform-independent, no
  compatibility concern.
- **License**: not applicable (metadata-only tracking package, no `requires_dist`).
- **Decision**: accepted transitively; not independently evaluated further since it carries no
  code or VTK-relevant behavior of its own.

## `cadquery` (already a project dependency — not newly introduced, version unchanged from what
`pyproject.toml` already declares: `cadquery>=2.5,<3`)

- **Version installed for this evaluation**: 2.8.0 (latest satisfying the existing project range,
  installed with `--no-deps` to control exactly which of its own dependencies get pulled in).
- **Not re-evaluated as a "new" dependency** — it is already the project's own pinned CAD library.
  Its own `requires_dist` was read from the actually-installed package metadata (not guessed) to
  determine the minimal real dependency set needed alongside `cadquery-ocp-novtk` (see
  `Experiment.md` step 2).

## `vtk`, `trame`, `trame-vtk`, `trame-components`, `trame-vuetify` — deliberately excluded

- **Purpose (upstream)**: `vtk` backs `cadquery-ocp`'s bundled visualization; `trame`/`trame-vtk`/
  `trame-components`/`trame-vuetify` back CadQuery's own optional Jupyter/web viewer
  (`cadquery.vis`), unused anywhere in ZeroRodCAD (`Discovery.md` CAD-engine module layout — no
  `zerorodcad*` file references `cadquery.vis` or the trame viewer).
- **Decision**: not installed, by design — this is the entire subject of the evaluation.

## Standard-library / already-vendored code reused (no new dependency)

Per the governance preference order (stdlib → existing gepflegte ZeroRodCAD dependency → official
framework API → small actively-maintained external dependency), every other piece of TE-001's PoC
code reuses what already exists in the repository or the standard library:

- `importlib.abc.MetaPathFinder`, `sys.meta_path` (stdlib) — `VTKImportBlocker`.
- `subprocess`, `json`, `pathlib`, `tempfile`, `argparse`, `traceback`, `re` (stdlib) — checkpoint
  runner, orchestrator, IVtk boundary probe, OS-level evidence probe.
- `src/zerorod_analysis/runtime/*` and `tools/trace_runtime.py` (existing, gepflegte ZeroRodCAD
  Build 021 M1 infrastructure) — runtime trace adapter, reused verbatim per `Discovery.md`.
- `zerorodcad.parameters` / `zerorodcad.model` / `zerorodcad.preview` / `zerorodcad.export`
  (existing, productive ZeroRodCAD API) — the actual checkpoints under test.
- `lsof`, `vmmap`, `du` (macOS system tools, not Python packages) — OS-level evidence and size
  measurement.

No archived, abandoned, or otherwise unmaintained package was used at any point in TE-001.
