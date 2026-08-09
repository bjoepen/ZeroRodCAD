# ADR-DRAFT — Tauri v2 + Python Engine Sidecar + No-VTK CadQuery + Three.js Preview

**Status: SUPERSEDED.** This draft's proposed architecture was carried forward, refined by
TE-002.1/TE-002.2A/TE-002.2B, and formally accepted in
[`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`](../../adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md)
(Status: Accepted, 2026-08-09). This document is kept as-is, unmodified below this notice, as the
historical research record of the point-in-time reasoning that led there — it is not deleted and
not rewritten to look as if it always said what the final ADR says.

**Original status note (superseded, kept for history): DRAFT — not a productive ADR.** Written
because Gate D = PASS (section 36). This document sketches a *possible* target architecture for
discussion; it commits the project to nothing and does not authorize any implementation work.

## Context

TE-001 → TE-001.1 → TE-001.2 → TE-002 progressively established: (1) ZeroRodCAD's own engine never
needed VTK, (2) a small, mechanical CadQuery patch removes VTK's incidental import-time coupling,
(3) that patch survives real PyInstaller packaging with a measured 58.25% bundle-size reduction,
and (4) a Tauri v2 + Python-sidecar + Three.js architecture can drive the same unmodified engine
through a clean, versioned, no-VTK, no-PySide6 contract.

## Proposed target architecture

```
Tauri v2 GUI
    +
Python Engine Sidecar (zerorod-sidecar/v1 over stdin/stdout)
    +
No-VTK CadQuery/OCP (CadQuery 2.8.0 + upstream-track patch + cadquery-ocp-novtk)
    +
PreviewMesh Contract (zerorod-mesh/v1)
    +
Three.js (BufferGeometry, OrbitControls)
```

## Advantages

- Removes ~530 MiB / 58% of packaged app size (VTK), measured (TE-001.2).
- Keeps the entire CAD engine (`zerorodcad.*`) unchanged — the sidecar is a thin transport shim,
  not a rewrite.
- Smaller WebView-facing IPC/capability surface than a naive shell-plugin-in-frontend design
  (TE-002's own architecture decision, `Tauri-Architecture.md`).
- Modern, actively maintained toolchain throughout (Tauri v2, Three.js current stable) instead of
  an aging PySide6/VTK stack.
- `PreviewMesh` already proved renderer-agnostic across two completely different consumers now
  (the existing `QPainter` widget, and Three.js) — validates it as a stable internal contract
  worth keeping either way, independent of this ADR's outcome.

## Disadvantages / open costs

- Introduces a second GUI technology stack (Rust/Tauri/JS) alongside Python — real maintenance
  surface, real hiring/skills implication, not evaluated here.
- Onefile sidecar packaging has a measured ~15 s cold-start cost per request as currently built —
  must be resolved (onedir packaging, or a persistent/reused sidecar process) before this is
  production-viable UX-wise.
- CadQuery's VTK decoupling is still a locally-applied patch, not upstream — an ongoing
  maintenance liability until resolved (tracked since TE-001.1).
- Full desktop-app feature parity (settings, project management, export dialogs, everything beyond
  the CAD preview) is completely unaddressed by TE-001/TE-001.1/TE-001.2/TE-002 — this ADR sketch
  covers only the preview/engine slice.
- Live interactive UX was not confirmed end-to-end in any TE-002 session (environment-constrained,
  not architecture-constrained) — a real production decision needs this closed first.

## Risks

Same list as `Conclusion.md`'s "Welche Risiken bleiben?" — onefile latency, unclosed interactive
verification, PoC-only `preview` command (no parametrization), no in-flight-sidecar cleanup on
window close, unresolved upstream CadQuery patch status.

## Migration strategy (sketch only, not a plan)

Would need, at minimum, before any real migration commitment: (1) upstream or wheel-pin the
CadQuery patch, (2) resolve sidecar startup latency, (3) extend the sidecar contract to the full
`ZeroRodParameters` surface (not just defaults), (4) design/scope full feature parity separately —
none of which TE-002 attempted or is qualified by itself to plan.

## Rollback strategy (sketch only)

None needed yet — nothing productive has changed. If a future migration were attempted and needed
reversal, the existing PySide6 app remains the fallback exactly as-is, since TE-001/TE-001.1/
TE-001.2/TE-002 never modified it.

## Explicitly not decided by this draft

Whether to actually pursue this architecture, on what timeline, with what resourcing, or whether
to instead invest in improving the existing PySide6 path. This ADR draft documents that the
*technical* question has a favorable answer; it does not answer the *product/roadmap* question.
