# TE-002.2B — Import-Origin Analysis (scipy / numba / llvmlite)

## Declared origin: CadQuery's own package metadata

`importlib.metadata.metadata("cadquery")["Requires-Dist"]` (in `.venv-novtk-bundle`) lists `scipy`
and `numba` as **unconditional** (non-`extra`) dependencies — not behind any optional-feature
marker. `llvmlite` is not listed directly; it is `numba`'s own transitive dependency. This is why
`pip install cadquery` installs all three, and why they are present in the venv PyInstaller reads
from — but installed-as-a-dependency is a packaging-metadata fact, not proof of a real code path.

## Static source origin: exactly one file in the whole `cadquery` package

```
grep -rEln "^\s*(import (numba|scipy)(\.|\s|$)|from (numba|scipy)[ .]import)" cadquery/
→ cadquery/occ_impl/nurbs.py   (only match, anywhere in the package)
```

`nurbs.py` does `import scipy.sparse as sp` and `from numba import njit as _njit` — used by its
NURBS curve/surface fitting implementation.

## Reachability: `nurbs.py` is not on ZeroRodCAD's import path

`nurbs.py`'s only importer is `cadquery/vis.py` (`from .occ_impl.nurbs import Curve, Surface`) —
CadQuery's interactive 3D visualization helper (`cadquery.vis.show`), unrelated to CAD modeling,
STL/STEP export, or the mesh-preview pipeline ZeroRodCAD uses. `cadquery/__init__.py` never
imports `.vis` (confirmed by reading the full file: it imports `occ_impl.geom`, `occ_impl.shapes`,
`occ_impl.exporters`, `occ_impl.importers`, `selectors`, `sketch`, `cq`, `assembly`, `types`,
`plugins` — no `vis`). Neither `zerorodcad/model.py`, `zerorodcad/preview.py`, nor
`zerorodcad/export.py` import `cadquery.vis` either. The sidecar's own `hiddenimports`
(`tools/poc/tauri/sidecar-onedir.spec`) list `OCP.*`, `cadquery`, `cadquery.exporters`,
`cadquery.occ_impl`, `casadi` — none of which reach `cadquery.vis`.

## Ground-truth runtime confirmation (the decisive check)

```python
import sys
before = set(sys.modules)
import cadquery
after = set(sys.modules)
# numba -> 0 modules loaded
# scipy -> 0 modules loaded
# llvmlite -> 0 modules loaded
```

Run directly in `.venv-novtk-bundle` (the exact build environment). A plain `import cadquery` —
before any ZeroRodCAD code executes — never touches `numba`/`scipy`/`llvmlite`. This matches all
four runtime traces in `Runtime-Evidence.md` (0 hits each) and is stronger evidence than "not
observed in one trace": it is a direct proof that the real, only source-level import path is
inert for every workflow ZeroRodCAD's code exercises.

## PyInstaller hook check

No `hook-cadquery.py` exists anywhere in `.venv-novtk-bundle` (checked `PyInstaller/hooks/` and
`_pyinstaller_hooks_contrib/stdhooks/`) — nothing forces `collect_submodules('cadquery')` or
similarly over-collects `cadquery.vis`. `hook-numba.py` and `hook-llvmlite.py` do exist in
`_pyinstaller_hooks_contrib`, but hooks only customize collection of a module *already* in the
dependency graph — they do not explain how `numba`/`llvmlite`/`scipy` got into the graph in the
first place. (PyInstaller's own static bytecode scanner is more conservative than actual runtime
import behavior — the mechanism by which the *unreachable* `nurbs.py` still ends up analyzed
was not further reverse-engineered beyond this point, since it does not change the actionable
conclusion below; scanner internals are out of scope for a bundle-optimization TE.)

## Conclusion

scipy/numba/llvmlite are present in the bundle because CadQuery declares them as hard dependencies
for its NURBS-visualization feature (`cadquery.vis`) — a feature ZeroRodCAD's own code never
imports, directly or transitively, at either the protocol level or the library level. This is a
conservative-collection artifact, not a functional necessity. This finding is what justifies
actually testing removal in `Optimization-C-Numba-Llvmlite.md` / `Optimization-D-Scipy.md`, per
the mandate's rule: "keine Entfernung, solange der Ursprung nicht verstanden ist."
