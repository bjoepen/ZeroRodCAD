# TE-002.2B — Optimization C: numba / llvmlite Exclusion

## Precondition met

`Runtime-Evidence.md`: NOT OBSERVED across all 4 broader traces (preview default, preview
alternate params, STL+STEP export, invalid-parameter error path). `Import-Origins.md`: the only
source-level import (`cadquery/occ_impl/nurbs.py`) is unreachable from ZeroRodCAD's actual code,
confirmed both statically and by direct runtime check (`import cadquery` loads 0 numba/llvmlite
modules).

## Change

Added `"numba"`, `"llvmlite"` to `excludes` in `tools/poc/tauri/sidecar-onedir.spec` (isolated —
`scipy` was *not* excluded in this experiment, tested independently in
`Optimization-D-Scipy.md`). Spec-level PyInstaller exclusion, not an environment uninstall — the
dev/build venv (`.venv-novtk-bundle`) keeps numba/llvmlite installed throughout, per the mandate's
explicit instruction to separate runtime requirement from installation metadata.

## Isolated measurement (standalone onedir sidecar, C alone)

| | Bytes | MiB | Files |
|---|---:|---:|---:|
| Baseline onedir | 451,767,301 | 430.84 | 290 |
| C only | 317,273,054 | 302.57 | 272 |
| **Savings** | **134,494,247** | **128.27** | **18** |

0 `numba`/`llvmlite` files present in the rebuilt tree (confirmed by `find -iname`).

## Validation

- `find -iname "*numba*" -o -iname "*llvmlite*"` on the rebuilt tree: 0 matches.
- Real persistent-protocol round trip: cold `preview` (720+146 vertices, matches reference), 4
  more repeated `preview` requests, an intentionally-invalid-parameter request (correctly rejected
  with `unsupported_parameters`, proving the protocol's own validation path is unaffected), clean
  `shutdown` (exit code 0), 0 orphan processes afterward.
- STL+STEP export via `export-probe` stimulus: both files created successfully
  (`cbg-open-g-body.stl`, `cbg-open-g-assembly.step`).
- `pytest tests/poc/tauri/ -q`: 48/48 pass.
- `pytest -q` (full repo regression suite): 241 passed, 1 pre-existing unrelated skip — identical
  to the pre-change baseline, zero new failures.

## Accepted

numba/llvmlite exclusion is **ACCEPTED**. Real, isolated savings of 128.27 MiB at the sidecar
level, zero functional regression across the full validation matrix. Classification upgraded from
TE-002.2A's "NOT OBSERVED" to **NOT REQUIRED** for any ZeroRodCAD-exercised code path (backed by
both static unreachability and a passing full functional/regression suite with the exclusion
applied) — not an absolute "never used by CadQuery anywhere" claim, which remains out of scope.
