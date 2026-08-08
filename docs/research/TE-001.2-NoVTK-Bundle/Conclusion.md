# TE-001.2 — Conclusion

## Gate C: PASS

All section-23 PASS criteria are met, verified in this session, not assumed:

| Criterion | Status |
|---|---|
| Python 3.13 | ✓ 3.13.14 |
| No-VTK packaging environment reproducible | ✓ `.venv-novtk-bundle`, documented install sequence (`Packaging.md`) |
| cadquery-ocp-novtk installed | ✓ 7.9.3.1.1 |
| cadquery-ocp not installed | ✓ |
| vtk not installed | ✓ |
| TE-001.1 patch active | ✓ verified via `import cadquery` under `VTKImportBlocker` before build |
| PyInstaller build successful | ✓ `Build complete!`, no fatal errors |
| App startet | ✓ `--diagnose`, `--startup-test`, real on-screen launch |
| Geometry funktioniert | ✓ byte-identical STEP output to source-level |
| PreviewMesh funktioniert | ✓ `stimulus-complete` for preview-probe |
| Preview validiert | ✓ AUTOMATED at the mesh-contract level; pixel-level NOT VERIFIED (disclosed, not faked) |
| STL funktioniert | ✓ 116984 bytes, byte-identical to source-level |
| STEP funktioniert | ✓ 105003 bytes, byte-identical to source-level |
| statisches Bundle enthält kein echtes VTK | ✓ 0 files / 0 bytes, four independent search methods |
| Runtime Trace beobachtet kein VTK | ✓ both profiles, `vtk_evidence()` → `[]` |
| OS-Level beobachtet kein VTK | ✓ `lsof`/`vmmap` both succeeded, 0 real hits (not `NOT VERIFIED`) |
| keine manuelle VTK-Löschung nach Build | ✓ never deleted anything; bundle was clean from the build itself |
| Bundlegröße real gemessen | ✓ Scanner 2.0, `du -sh` corroborating |
| Vergleich zur Baseline dokumentiert | ✓ `Size-Comparison.md`, baseline clearly labeled HISTORICAL |

No FAIL or INCONCLUSIVE trigger applies: the app is fully packageable without VTK, starts, and
every core workflow (geometry, tessellation, preview mesh, STL, STEP) works identically to the
non-packaged, source-level TE-001.1 result — same byte-exact output sizes, in fact.

## Evidence Confidence: HIGH

All five evidence layers (package, functional, static bundle, runtime trace, OS-level) completed
and agree. The only sub-item marked `NOT VERIFIED` is pixel-level visual screenshot confirmation of
the rendered preview widget — a single, explicitly-disclosed, permission-constrained limitation
within the "Preview" criterion, not a missing evidence layer; the underlying mesh-generation
contract that widget renders from (`PreviewMesh`/`build_preview_scene()`) is independently
confirmed AUTOMATED via the runtime-trace stimulus. This does not reduce confidence below HIGH.

## Real measured size saving

**530.39 MiB reduction (58.25%)** — 910.51 MiB (historical VTK baseline) → 380.12 MiB (measured
no-VTK build). VTK itself accounted for 584.10 MiB / 364 files in the baseline, now 0 MiB / 0
files. See `Size-Comparison.md` for the full breakdown and an honest accounting of unrelated
build-to-build noise in the Frameworks/PySide6 rows.

## CadQuery patch deployment recommendation (section 25 — evaluated, not implemented)

Assessed options:

- **A. Upstream fix in CadQuery** — preferred long-term target, per the mandate's own stated
  preference. TE-001.1's `Patch-Analysis.md` already frames the patch as a plausible upstream
  discussion basis (small, mechanical, backward-compatible) and links it to the still-open
  CadQuery/cadquery#1908. Not something this evaluation can cause to happen; a follow-up action
  item, not a TE-001.2 deliverable.
- **B. Temporarily maintained patch during packaging** — **the pragmatic near-term choice**, now
  that TE-001.2 has demonstrated the patch applies cleanly not just at the source/venv level
  (TE-001.1) but through the *entire* real packaging pipeline (this evaluation): copied into an
  isolated packaging venv, survives a full PyInstaller build, and produces byte-identical
  functional output to the unpatched-source baseline. If ZeroRodCAD wanted a no-VTK production
  build today, applying this exact, version-pinned patch as a documented pre-packaging step (e.g.
  a small script mirroring what `Packaging.md` describes) is technically ready to do.
- **C. Own reproducible wheel** — would formalize option B (build and publish a patched
  `cadquery` wheel pinned to 2.8.0) instead of a copy-files step. Not evaluated in depth here — a
  reasonable next increment on top of B if B's manual-copy approach proves inconvenient in
  practice, not something TE-001.2's scope required deciding.
- **D. Other transition strategy** — none identified beyond A/B/C.

**No permanent fork was created.** Recommendation: pursue A as the long-term goal; if a production
build is needed before A lands, B (exactly as demonstrated in this evaluation, version-pinned and
documented) is a reasonable, low-risk interim step — this is an assessment for a future, separately
scoped decision, not something TE-001.2 implements.

## TE-002 (Tauri v2 + Three.js Preview Architecture): GO, conditioned on the patch question

Per section 24, Gate C = PASS means TE-002 **may be recommended** (not implemented). Consistent
with TE-001.1's own conditional framing, extended now that the full packaging pipeline is proven:

**GO**, provided the CadQuery patch (or an equivalent — upstream fix or a formalized wheel) becomes
an actual, documented, reproducible part of the production toolchain before TE-002 ships anything
depending on it. TE-001.2 removes the last major open question from TE-001/TE-001.1's own stated
limitations ("kein produktives PyInstaller-Bundle... Bundle-Größenvergleich bleibt ausstehend") —
that gap is now closed with real, measured evidence. The architectural direction (`Shape.
tessellate()` → `PreviewMesh` → Three.js `BufferGeometry`, per the target diagram in the mandate)
is technically justified by everything measured across TE-001/TE-001.1/TE-001.2: ZeroRodCAD's own
engine never needed VTK, a small patch removes CadQuery's incidental VTK coupling, and that patch
survives real production packaging with a measured 58% bundle-size reduction and zero functional
regressions.

## Known limitations

- Baseline is historical, not rebuilt in this session (deliberate, mandate-sanctioned — see
  `Discovery.md`/`Size-Comparison.md`); the two bundles come from different build sessions, so
  small non-VTK deltas (Frameworks/PySide6) carry some session-to-session noise the VTK figure
  itself does not.
- Pixel-level visual confirmation of the rendered preview widget was attempted but blocked by a
  screen-recording permission constraint in this environment — disclosed as `NOT VERIFIED`, not
  faked. The underlying mesh-generation contract is independently confirmed.
- Startup time was not measured (no existing automated timing harness; building one was out of
  scope).
- Code signing/notarization was explicitly out of scope (ad-hoc signing only, per the mandate) —
  Gatekeeper/distribution readiness is not evaluated here.
- Two pre-existing, VTK-unrelated PyInstaller hidden-import errors (`OCP.TKernel`,
  `cadquery.exporters`) were observed and did not block the build; not investigated further as
  out of scope.
- This evaluation is scoped to the exact versions already pinned throughout TE-001/TE-001.1/
  TE-001.2 (CadQuery 2.8.0, `cadquery-ocp-novtk` 7.9.3.1.1, PySide6 6.11.1, PyInstaller 6.21.0). A
  version change anywhere in that chain would require re-running the relevant parts of this
  evaluation, not assuming this conclusion still holds.
