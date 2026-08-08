# TE-002.2A — Conclusion

## Why the app is ~700 MB, in one sentence

Because the Python CAD-engine sidecar (OCP + its native dependency set) is bundled **twice** —
once onefile-packaged (135.45 MiB, kept as TE-002's original fallback path) and once onedir-
packaged (525.48 MiB, TE-002.1's recommended default path) — together 660.93 MiB, 98.15% of the
app; the Tauri/Rust/frontend GUI layer itself is only 13.04 MiB.

## Is the 700 MB "fully necessary"? Neither yes nor no — documented, not decided

Some of it clearly is: OCP (216.18 MiB) is the CAD kernel, confirmed load-bearing by every prior
TE. Some of it is clearly structural, not a dependency question: the duplicate onefile+onedir
sidecar packaging (135.45 MiB) exists because TE-002.1 kept both variants for its own comparison,
and 93.90 MiB of hash-verified duplicate dylibs inside the onedir copy exist because of how
PyInstaller and the OCP wheel each independently collect the same native libraries. And some of it
is genuinely uncertain: llvmlite (122.78 MiB) and scipy (31.75 MiB) were not observed in the one
runtime trace captured so far — not proof they're unused, just not yet confirmed used
(`Candidates.md`).

## Delta vs. the 380.12 MiB PySide6 reference

+293.22 MiB total. +72.04 MiB is confidently attributed (duplicate sidecar packaging, PySide6/Qt
removed, Tauri/Rust added, OCP/casadi unchanged). +221.18 MiB remains an honestly-marked
UNEXPLAINED-WITH-PLAUSIBLE-CAUSE remainder — plausibly llvmlite+scipy+numpy+Python-runtime+misc,
but Scanner 2.0's category granularity can't confirm this against the PySide6 baseline without a
same-tool re-scan of that bundle, not performed here (`Delta-Analysis.md`).

## Gate F-A: PASS

- Real app size exactly measured (multiple units, cross-checked): **YES**
- Sidecar size known (both copies, broken down): **YES**
- Top contributors known (top 5 files, top-level map): **YES**
- Python/OCP share known: **YES** (216.18 MiB / 42.5% of the onedir sidecar's `_internal`)
- Tauri/Frontend share known: **YES** (13.04 MiB, <2% of the app)
- VTK = 0 confirmed: **YES** (three independent methods)
- PySide6/Qt = 0 confirmed: **YES** (two independent methods)
- Duplicates investigated: **YES** (hash-based, 77 groups, 93.90 MiB, plus the structural
  onefile/onedir duplication)
- Delta to 380.12 MiB largely explained: **PARTIALLY** — 72.04 MiB confidently, 221.18 MiB
  plausibly but not confirmed, explicitly marked as such rather than forced to fit
- TE-002.2B candidates identified: **YES** (`Candidates.md`, 5 items with evidence status)
- No optimization performed: **CONFIRMED** — bundle fingerprint identical before/after, no source,
  config, dependency, or architecture file was touched

Not INCONCLUSIVE: no essential part of the bundle went unattributed — even the honestly-marked
delta remainder has a specific, itemized, plausible composition, just not a fully confirmed one.
Not FAIL: nothing here contradicts or undermines any prior TE's findings — OCP is unchanged,
VTK/PySide6 are still confirmed absent, and the size is fully accounted for at the file level even
where its *comparison* to the historical baseline can't be closed to the last MiB.

## Gate E is not revisited

TE-002.2A does not change Gate E-A (PASS, TE-002.1) or the user's positive human validation result
(app starts, model renders, rotation works, preview functions within its PoC scope) — this
evaluation only decomposes what the resulting bundle is made of. `ADR-DRAFT-TE0021.md` remains a
draft; no ADR was finalized, no productive migration was started, no dependency was removed, no
PyInstaller configuration was changed.

## Recommended next step

**TE-002.2B** — investigate the identified candidates (llvmlite/numba/scipy runtime necessity
across a broader trace set; whether the duplicate onefile sidecar is still needed once Variant D
is the sole target; whether the 93.90 MiB duplicate-dylib pattern can be safely deduplicated by
PyInstaller configuration) before any actual size-reduction change is made. Per this evaluation's
own governing discipline: measure → attribute → explain now; change → rebuild → compare only in
TE-002.2B.
