# TE-001 — Experiment

Exact commands run for TE-001, in order. All commands run from the repository root, on the
`spike/te001-novtk-feasibility` branch. `.venv` was never modified.

## 1. Isolated environment

```
python3.13 -m venv .venv-novtk-poc
./.venv-novtk-poc/bin/python -c "import sys; print(sys.version)"
./.venv-novtk-poc/bin/python -c "import site; print(site.getsitepackages())"
./.venv-novtk-poc/bin/python -c "import sys; print('base_prefix', sys.base_prefix); print('prefix', sys.prefix)"
```

Result: Python 3.13.14; single isolated site-packages path under `.venv-novtk-poc`; `prefix` !=
`base_prefix` confirming no `--system-site-packages` leakage.

## 2. Installation

```
./.venv-novtk-poc/bin/python -m pip install --upgrade pip
./.venv-novtk-poc/bin/python -m pip install "cadquery-ocp-novtk==7.9.3.1.1"
./.venv-novtk-poc/bin/python -m pip install "cadquery==2.8.0" --no-deps
./.venv-novtk-poc/bin/python -m pip install \
  "ezdxf>=1.3.0" "multimethod<2.0,>=1.11" "nlopt<3.0,>=2.9.0" "runtype" "casadi" \
  "pyparsing>=3.0.0" "scipy" "numba"
./.venv-novtk-poc/bin/python -m pip install -e . --no-deps   # installs zerorodcad-desktop itself, editable
```

The explicit dependency list in step 3 is `cadquery==2.8.0`'s own `requires_dist`
(`cadquery-ocp, casadi, ezdxf, multimethod, nlopt, numba, pyparsing, runtype, scipy, trame,
trame-components, trame-vtk, trame-vuetify`) minus `cadquery-ocp` (replaced by the novtk variant)
and minus `trame`/`trame-components`/`trame-vtk`/`trame-vuetify` (CadQuery's optional Jupyter/trame
viewer, not used anywhere in ZeroRodCAD — confirmed in `Discovery.md`). Nothing was guessed:
this list came directly from `pip show cadquery`'s `Requires:` field read against the actually
installed package.

`cadquery-ocp`, `vtk`, and `trame*` were never installed.

## 3. Package audit

```
./.venv-novtk-poc/bin/python -m pip list
./.venv-novtk-poc/bin/python -m pip show cadquery cadquery-ocp cadquery-ocp-novtk vtk
./.venv-novtk-poc/bin/python -m pip check
```

`pip show cadquery-ocp` and `pip show vtk` both returned
`WARNING: Package(s) not found` (i.e., confirmed absent).

`pip check` output (verbatim):
```
cadquery 2.8.0 requires cadquery-ocp, which is not installed.
cadquery 2.8.0 requires trame, which is not installed.
cadquery 2.8.0 requires trame-components, which is not installed.
cadquery 2.8.0 requires trame-vtk, which is not installed.
cadquery 2.8.0 requires trame-vuetify, which is not installed.
```
This is the expected metadata-naming mismatch from section 8 of the mandate (`cadquery`'s formal
metadata names `cadquery-ocp`, not knowing `cadquery-ocp-novtk` satisfies the same import
namespace) plus the deliberately-omitted `trame*` viewer extras. No package metadata was edited
or faked. This is **not** treated as a Gate A failure by itself.

## 4. Bare-import risk check (before building the checkpoint harness)

```
./.venv-novtk-poc/bin/python -c "import cadquery"
```
Result: `ModuleNotFoundError: No module named 'vtkmodules'` — confirming the static-analysis
finding in `Discovery.md` empirically, before any blocker was installed.

Full traceback captured separately with the blocker installed (see `Results.md` for the exact
file/line):
```
./.venv-novtk-poc/bin/python -c "
import sys; sys.path.insert(0, '.')
from tools.poc.novtk.vtk_import_blocker import install
install()
import traceback
try:
    import cadquery
except Exception:
    traceback.print_exc()
"
```

## 5. Gate A checkpoint run

```
./.venv-novtk-poc/bin/python tools/poc/novtk/run_checkpoints.py \
  --report build/reports/te001-novtk-poc/checkpoints.json \
  --raw-trace build/reports/te001-novtk-poc/raw-trace.jsonl
```

## 6. IVtk boundary probe

```
./.venv-novtk-poc/bin/python tools/poc/novtk/ivtk_boundary.py \
  --report build/reports/te001-novtk-poc/ivtk-boundary.json
```

## 7. Full evidence run (orchestrates 5-6 plus OS-level evidence, sizes, package audit, Gate A decision)

```
python3.13 tools/poc/novtk/te001_run_all.py
```
Writes `build/reports/te001-novtk-poc/te001-full-evidence.json` (all evidence layers, sizes,
package audit and the final Gate A verdict) plus `runtime-trace.json` (the reused Build 021 M1
`RuntimeTrace`, serialized via `write_trace_atomic`). This orchestrator itself never imports
`cadquery`/`OCP` — it only reuses `zerorod_analysis.runtime`/`tools.trace_runtime` (pure Python)
to assemble the report from the subprocess outputs, so it runs under the plain `python3.13`
interpreter, not either venv.

## 8. Size measurements (real `du -sh`, not estimated)

```
du -sh .venv-novtk-poc
du -sh .venv-novtk-poc/lib/python3.13/site-packages/OCP
du -sh .venv-novtk-poc/lib/python3.13/site-packages/cadquery
```

## 9. Tests

```
./.venv/bin/python -m pytest tests/poc/novtk/ -v
./.venv/bin/python -m pytest -q   # full suite, regression check
```

## Known limitation hit during the experiment (documented, not silently worked around)

`DYLD_PRINT_LIBRARIES=1` on this machine prints lines shaped
`dyld[PID]: <UUID> /path/to/lib` — the reused `tools/trace_runtime.py:parse_dyld_output()` regex
expects the literal token `loaded:` in each line (a different dyld/macOS version's format), so it
matched 0 of 2222 real library-load lines from a checkpoint run. This is marked `NOT VERIFIED` for
that specific reused sub-mechanism (see `tools/poc/novtk/te001_run_all.py:check_dyld_parser_match`)
rather than silently treated as "0 VTK libraries found." `lsof -p PID` / `vmmap PID`
(both explicitly mandated by section 20 alongside dyld parsing) were used as the primary OS-level
mechanism instead and did succeed — see `Results.md`.

A second, unrelated false-positive was caught and fixed during this step: naive
`"vtk" in line.lower()` matching on `lsof`/`vmmap` output flagged every line for the process
simply because the PoC venv is named `.venv-novtk-poc` (the substring "vtk" appears inside
"novtk"). Fixed with a `(?<!no)vtk` regex (case-insensitive) that excludes the "novtk" token but
still matches real "vtk"/"VTK" occurrences — covered by
`tests/poc/novtk/test_os_evidence_token_regex.py`.
