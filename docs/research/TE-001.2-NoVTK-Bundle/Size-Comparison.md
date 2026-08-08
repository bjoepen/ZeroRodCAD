# TE-001.2 — Size Comparison

## Methodology note

BASELINE is **HISTORICAL** (reused per section 7 of the mandate, not re-built — see
`Discovery.md` for why this is the mandate-sanctioned choice). NO-VTK is **MEASURED** fresh in this
session. Both were produced by the same tool (`tools/scan_bundle.py`, Scanner 2.0) against the
same dependency versions (`cadquery` 2.8.0, `cadquery-ocp`/`cadquery-ocp-novtk` 7.9.3.1.1),
making the comparison methodologically apples-to-apples for the one variable this evaluation
isolates (VTK presence/absence). The two bundles were nonetheless built in different sessions —
see "Known limitations" below for what that does and doesn't affect.

## Comparison table

| | BASELINE (HISTORICAL) | NO-VTK (MEASURED) | DIFFERENCE |
|---|---:|---:|---:|
| App total | 910.51 MiB | 380.12 MiB | **−530.39 MiB** |
| Contents/Frameworks | 32.93 MiB | 64.50 MiB | +31.57 MiB |
| Contents/Resources | 1.72 MiB | 1.71 MiB | −0.01 MiB |
| OCP | 217.50 MiB (80 files) | 216.03 MiB (78 files) | −1.47 MiB / −2 files |
| VTK | 584.10 MiB (364 files) | **0.00 B (0 files)** | **−584.10 MiB / −364 files** |
| PySide6 | 56.74 MiB (168 files) | 76.60 MiB (224 files) | +19.86 MiB / +56 files |
| Qt | 604 B (12 files) | 1.63 KiB (30 files) | +1.03 KiB / +18 files |
| File count (total) | 1349 | 713 | **−636 files** |

Source: `build/reports/build-019.1-scanner2/scanner2-report.md` (baseline, re-confirmed byte-
identical in `build-019.3-m3/scanner2/scanner2-report.md`) vs.
`build/reports/te0012-novtk-bundle/scan/scanner2/scanner2-report.md` (no-VTK, this session).

## Reduction

```
Baseline App:  910.51 MiB
No-VTK App:    380.12 MiB
Reduction:     530.39 MiB
Reduction:     58.25 %
```

VTK alone accounts for **584.10 MiB** of the baseline — larger than the total reduction, because
Frameworks/PySide6/Qt grew slightly (see below), partially offsetting the pure VTK removal.

## Interpretation

The dominant effect is exactly what the isolated-variable design predicted: VTK's **584.10 MiB /
364 files** are entirely gone, and no VTK component appears anywhere in the new bundle by any
search method (`Bundle-Analysis.md`). OCP is essentially unchanged (−1.47 MiB, −2 files — noise-
level, consistent with OCP not being touched by this evaluation).

**Frameworks (+31.57 MiB) and PySide6 (+19.86 MiB, +56 files) grew.** This is a real, measured
difference, reported honestly rather than smoothed over — but it should **not** be read as "no-VTK
packaging makes PySide6 bigger." The two measurements come from different build sessions
(baseline: an earlier session's `dist/ZeroRodCAD Desktop.app`, per `build-019.1-scanner2`'s commit
context; no-VTK: this session, today). Plausible causes, none confirmed further since it's outside
this evaluation's scope: PyInstaller/`pyinstaller-hooks-contrib` version drift between sessions
changing exactly which Qt plugin files get collected, or minor packaging-environment differences
unrelated to the VTK/no-VTK axis. What *is* confirmed: this delta is unrelated to VTK — the
`Bundle-Analysis.md` VTK section is independently and unambiguously zero regardless of how
Frameworks/PySide6 partition.

## GEMESSEN vs. HISTORICAL vs. ESTIMATED — explicit labeling

- **MEASURED** (this session, `tools/scan_bundle.py` against the actual built bundle): No-VTK
  column, all rows.
- **HISTORICAL** (real measurement, different session, same tool, same dependency versions, cited
  with source file): Baseline column, all rows.
- **ESTIMATED**: none used in this comparison — no theoretical/projected numbers appear in the
  table above.

## Startup time

Not measured — no reliable, already-existing automated timing harness exists for this in the
current packaging infrastructure, and building one would exceed TE-001.2's scope ("keine neue
Analysefunktion entwickeln"). Not reported as a fabricated number; explicitly omitted rather than
guessed.

## Known limitations of this comparison

- Baseline and no-VTK bundles were built in different sessions (see interpretation above) — the
  VTK delta itself is unambiguous and isolated regardless, but the small Frameworks/PySide6 deltas
  cannot be attributed with full certainty to any single cause.
- No startup-time comparison performed (see above).
- The dead-library analyzer's 226.70 MiB "potential further savings" figure for the no-VTK bundle
  (`Bundle-Analysis.md`) is **not** included in the reduction figures above — it is a separate,
  lower-confidence estimate from a tool already known (per TE-001.1) to misclassify load-bearing
  libraries as removable, and is not comparable to the direct before/after measurement.
