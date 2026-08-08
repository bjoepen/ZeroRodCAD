# TE-001.2 — Bundle Analysis

Static analysis of `dist/ZeroRodCAD Desktop.app`, produced by:
```
python tools/scan_bundle.py "dist/ZeroRodCAD Desktop.app" \
  --output-dir build/reports/te0012-novtk-bundle/scan --dead-libraries --macho-dependencies --no-cache
```
using the existing Scanner 2.0 tooling (`src/zerorod_analysis/`) verbatim — no new analysis engine.

## Totals

- Files: **713**, Directories: **221**, Total size: **380.12 MiB**, Symlinks: **264**, Mach-O
  files: **288**, `du -sh`: **381M**.

## Bundle sections (`scanner2-inventory.json` → `statistics.section_sizes`/`section_counts`)

| Bereich | Dateien | Größe |
|---|---:|---:|
| MacOS | 1 | 12.16 MiB |
| Frameworks | 253 | 64.50 MiB |
| Resources | 122 | 1.71 MiB |
| PlugIns | 0 | 0.00 B |
| PySide6 | 224 | 76.60 MiB |
| Qt | 30 | 1.63 KiB |
| **VTK** | **0** | **0.00 B** |
| OCP | 78 | 216.03 MiB |
| casadi | 3 | 8.98 MiB |
| Python | 0 | 0.00 B |
| Executables | 0 | 0.00 B |
| Other | 2 | 141.27 KiB |

## VTK search (section 13, explicit)

| Method | Result |
|---|---|
| `find "dist/ZeroRodCAD Desktop.app" -iname "*vtk*"` | 0 matches |
| `find "dist/ZeroRodCAD Desktop.app" -iname "*IVtk*"` | 0 matches |
| Scanner 2.0 `section_sizes["VTK"]` / `section_counts["VTK"]` | 0 bytes / 0 files |
| Naive substring `"vtk" in relative_path.lower()` over all 713 inventoried files | 0 matches |

**No VTK.framework, no libvtk*.dylib, no vtkmodules directory, no IVtk anything** — the bundle
contains zero VTK components by every method tried, including a search broader than the
classifier's own logic.

### On the known false positive (explicitly checked, not just assumed absent)

TE-001.1 documented that a naive check could misflag `cadquery.occ_impl.exporters.vtk` (the
patched, legitimately-named, VTK-free-until-called module) as VTK evidence. Confirmed here that
this file **does exist** in the bundle's Python module graph (as `cadquery/occ_impl/exporters/
vtk.py`, bundled by PyInstaller inside `Contents/Frameworks/cadquery/occ_impl/exporters/vtk.py` —
observed directly in the runtime trace, see `Runtime-Validation.md`), and confirmed the corrected
TE-001.1 heuristic (file-path-**segment** exact match on `"vtkmodules"`, not a substring search,
per `src/zerorod_analysis/scanner/classification.py::classify_section()`) does **not** misclassify
it: the file's path segments are `("Contents","Frameworks","cadquery","occ_impl","exporters",
"vtk.py")` — no segment equals `"vtkmodules"`, so `classify_section()` correctly does not return
`BundleSection.VTK` for it. This is exactly why the Scanner 2.0 VTK count is a trustworthy `0`,
not an accidentally-suppressed false negative.

## OCP

78 files, 216.03 MiB — the CAD kernel binaries, correctly bundled (largest single file:
`Contents/Frameworks/OCP/OCP.cpython-313-darwin.so`, 139.54 MiB). Present and load-bearing, as
expected — TE-001.2 does not touch OCP itself, only the VTK dependency alongside it.

## PySide6 / Qt

PySide6: 224 files, 76.60 MiB. Qt: 30 files, 1.63 KiB (the platform/image-format plugins under
`Contents/Frameworks/PySide6/Qt/plugins/`, correctly filtered down to what the existing spec's
46-entry Qt module exclude list allows through — unchanged by this evaluation).

## Bundle health (dead-library analyzer, supplementary context only)

`optimization-plan.md`: **Bundle Health 68/100 (fair)**, 454 analyzed library units, 358 flagged
`SAFE REMOVE`, 226.70 MiB potential savings claimed. **Caveat carried over from TE-001.1's own
documented finding**: this analyzer's removal *recommendations* are known to be unreliable — it
flags `Contents/Frameworks/OCP/OCP.cpython-313-darwin.so` itself (139.54 MiB) as "SAFE REMOVE"
with "No Mach-O dependency was found," which is almost certainly a false positive (OCP is the CAD
kernel binding; the app cannot function without it — confirmed functionally in
`Runtime-Validation.md`). The health *score* and *size totals* are treated as informational
context; the specific removal candidate list is **not** treated as actionable evidence for this
evaluation, consistent with how TE-001.1 treated the same tool's output on a different bundle.
