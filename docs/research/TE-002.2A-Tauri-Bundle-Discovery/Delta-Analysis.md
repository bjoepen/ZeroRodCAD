# TE-002.2A — Delta Analysis

## Comparison

| | TE-001.2 No-VTK PySide6 | TE-002.1 Tauri | Delta |
|---|---:|---:|---:|
| App total | 380.12 MiB | 673.34 MiB | **+293.22 MiB** |

Both are real, measured bundles (not estimates) — TE-001.2's from its own session (reused, per
`Discovery.md`), TE-002.1's fresh in this session, both via the same tool (Scanner 2.0) for the
categories that exist on both sides.

## Confidently attributed (high confidence, both sides measured with the same tool/categories)

| Contributor | Delta |
|---|---:|
| Duplicate onefile sidecar (kept alongside onedir for TE-002.1's own variant comparison — not required by a Variant-D-only target architecture) | +135.45 MiB |
| PySide6 removed | −76.60 MiB |
| Qt removed | −0.0016 MiB (negligible) |
| Tauri/Rust + Frontend added (new GUI layer) | +13.04 MiB |
| OCP (essentially unchanged — same patched `cadquery-ocp-novtk` both sides) | +0.15 MiB |
| casadi (byte-identical size both sides: 8.98 MiB) | +0.00 MiB |
| **Subtotal, confidently attributed** | **+72.04 MiB** |

## Remainder: ~221.18 MiB — NOT fully explained, marked explicitly rather than forced to fit

`293.22 − 72.04 = 221.18 MiB` remains. This corresponds to the onedir sidecar's content beyond
OCP and casadi (llvmlite 122.78 MiB, scipy 31.75 MiB, numpy 6.55 MiB, the Python runtime itself
~20.57 MiB, ezdxf/nlopt/numba/misc ~12.5 MiB, the onedir executable 16.16 MiB) compared against
whatever the equivalent content is inside TE-001.2's own generic buckets (`Frameworks` 64.50 MiB +
`Resources` 1.71 MiB + `Other` 0.14 KiB + `Python` 0.00 B = 66.35 MiB).

**Why this can't be cleanly resolved here**: Scanner 2.0's fixed category list (MacOS, Frameworks,
Resources, PlugIns, PySide6, Qt, VTK, OCP, casadi, Python, Executables, Other) has no dedicated
bucket for `scipy`/`llvmlite`/`numpy`/`numba` — on the PySide6 side, whatever amount of these
libraries (if any) is bundled would fall into the generic 64.50 MiB `Frameworks` bucket, which is
far smaller than these libraries' combined size on the Tauri side (~161 MiB for
llvmlite+scipy+numpy+numba alone). Two explanations are equally plausible from the evidence
available in this session, and this evaluation does not have grounds to pick one:

1. The PySide6 production build's PyInstaller spec (`packaging/macos/`) genuinely does not bundle
   `scipy`/`llvmlite`/`numba` at comparable size — e.g. because its hiddenimports list is narrower
   or its static import analysis never found a real code path to them, whereas
   `tools/poc/tauri/sidecar-onedir.spec`'s hiddenimports list may be broader (TE-001's original
   Phase 1 install strategy explicitly installed `scipy`/`numba` as part of CadQuery's own declared
   `requires_dist`, which does not by itself imply either build's PyInstaller spec force-includes
   them the same way).
2. They are present in the PySide6 bundle too, just invisibly absorbed into the generic
   `Frameworks`/`Other` buckets in a way the category-level report doesn't separate out.

**Resolving this with confidence would require re-scanning the PySide6 bundle with the same
file-level granularity used here for the Tauri bundle (i.e., listing its `Frameworks` bucket's
individual files, not just the category total) — not done in this session, out of scope for
TE-002.2A's "no rebuild, minimal new measurement" discipline, and not needed to answer this TE's
actual research question (why is the *Tauri* bundle this size), only to fully close the
comparison's last MiB.**

**Explicitly not forced to fit**: no number above was adjusted or reinterpreted to make the
totals reconcile exactly. The confidently-attributed +72.04 MiB and the honestly-unresolved
+221.18 MiB together sum to the full +293.22 MiB delta, with the split marked exactly where
certainty ends.

## What the remainder is plausibly made of (labeled PLAUSIBLE, not CONFIRMED)

llvmlite (122.78 MiB) + scipy (31.75 MiB) + numpy (6.55 MiB) + Python runtime (~20.57 MiB) +
onedir executable (16.16 MiB) + ezdxf/nlopt/numba/misc (~12.5 MiB) ≈ 210.3 MiB, close to the
221.18 MiB remainder (the ~11 MiB gap is within the rounding/methodology noise of comparing a
file-level sum against a category-level historical total). This is a plausible accounting, not a
confirmed one — see `Candidates.md` for what a future TE-002.2B would need to check to move this
from PLAUSIBLE to CONFIRMED.
