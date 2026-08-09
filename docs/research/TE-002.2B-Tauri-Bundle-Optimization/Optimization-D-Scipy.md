# TE-002.2B — Optimization D: scipy Exclusion

## Precondition met

Same evidence base as Optimization C (`Runtime-Evidence.md`, `Import-Origins.md`) — scipy's only
source-level import is the same unreachable `cadquery/occ_impl/nurbs.py`.

## Change (independent from Optimization C, per the mandate's independent-attribution requirement)

`numba`/`llvmlite` excludes from Optimization C were **reverted** first; `"scipy"` was added to
`excludes` in `tools/poc/tauri/sidecar-onedir.spec` alone, and the sidecar rebuilt from a clean
state before measuring — so this number is scipy's isolated contribution, not combined with C.

## Isolated measurement (standalone onedir sidecar, D alone)

| | Bytes | MiB | Files |
|---|---:|---:|---:|
| Baseline onedir | 451,767,301 | 430.84 | 290 |
| D only | 414,600,661 | 395.39 | 208 |
| **Savings** | **37,166,640** | **35.45** | **82** |

`numba`/`llvmlite` files still present in this build (3 matches for `*numba*`/`*llvmlite*`),
confirming the exclusion was genuinely scipy-only — a clean isolated variable.

## Validation

- `find -iname "*scipy*"`: 0 matches. `numba`/`llvmlite` still present (as expected, not excluded
  here).
- Real persistent-protocol round trip: cold `preview` correct, 3 more repeated requests, invalid-
  parameter rejection still correct, clean `shutdown` (exit 0), 0 orphans.
- STL+STEP export via `export-probe`: both files created successfully.
- `pytest tests/poc/tauri/ -q`: 48/48 pass.

## Accepted

scipy exclusion is **ACCEPTED** independently of Optimization C. Real, isolated savings of
35.45 MiB, zero functional regression. Same classification upgrade as C: NOT REQUIRED for any
ZeroRodCAD-exercised code path.
