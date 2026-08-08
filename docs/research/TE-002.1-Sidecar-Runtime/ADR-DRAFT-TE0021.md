# ADR-DRAFT-TE0021 — Persistent, Onedir-Packaged Sidecar Runtime

**Status: DRAFT — not a productive ADR.** Written because Gate E-A = PASS (`Conclusion.md`). This
document sketches a *possible* refinement to the TE-002 target architecture for discussion; it
commits the project to nothing and does not authorize any implementation work. It also does not
supersede TE-002's own `ADR-DRAFT.md` — it narrows one specific part of that sketch (the sidecar's
runtime/packaging strategy) based on evidence TE-002 didn't yet have.

## Context

TE-002 proved a Tauri v2 + Python-sidecar + Three.js architecture works end-to-end, but flagged
its onefile, one-shot sidecar packaging as a real, measured UX risk (~15 s per request) without
resolving it. TE-002.1 measured four concrete alternatives — onefile/onedir × one-shot/persistent
— rather than assuming a fix, per the mandate's explicit "measure, compare, document, then
recommend" rule.

## Proposed refinement

Replace TE-002's onefile, one-shot sidecar (`request_preview`) with a **persistent, onedir-packaged
sidecar** (`persistent_preview`) as the default runtime strategy, while keeping the original
one-shot command available as a fallback (not removed — both exist in the current PoC code,
`sidecar.js`'s `requestPreviewOneShot`).

```
Tauri v2 GUI
    +
Python Engine Sidecar, onedir-packaged, persistent process
(zerorod-sidecar/v1 over stdin/stdout — same schema TE-002 already established)
    +
No-VTK CadQuery/OCP (unchanged from TE-001.1/TE-001.2/TE-002)
    +
PreviewMesh Contract (zerorod-mesh/v1, unchanged)
    +
Three.js (unchanged)
```

## Advantages

- Cold start drops from ~15.8 s median (onefile one-shot) to ~0.64 s (onedir persistent) — a
  ~25× improvement, measured (`Performance.md`).
- Warm requests, after the first, cost ~0.13 s — effectively the engine's own tessellation time,
  with no packaging overhead at all.
- Removes a structural process-termination reliability risk that onefile has and onedir doesn't:
  a Rust-triggered forced kill (timeout, crash-recovery restart, app-exit cleanup) cannot orphan a
  worker process under onedir, because there's no forked worker to orphan (`Process-Lifecycle.md`).
- No change to the protocol, the mesh contract, or the WebView-facing IPC surface — this is a
  runtime/packaging decision, not an architecture change (`Security.md` confirms the capability
  surface is unchanged).
- The exact bundled artifact (not just a standalone copy) was proven to work through the real
  protocol, inside a real `tauri build` output — stronger evidence than TE-002 had for its own
  onefile approach.

## Disadvantages / open costs

- Disk footprint grows from 135 MiB/1 file to 525 MiB/368 files per sidecar copy — a real,
  measured cost, not weighed as decisive here but relevant to installer size (`Packaging.md`).
- A persistent process needs real lifecycle management (start, timeout, crash-detect, restart,
  shutdown, app-exit cleanup) that a one-shot process never needed — implemented here
  (`persistent.rs`) but adds real code and real failure modes (timeout handling, restart-once
  policy) that TE-002's simpler one-shot design didn't have to consider.
- No idle-timeout cleanup exists yet — the persistent engine stays resident until explicitly shut
  down, an app exit, or a failure triggers a restart. A production build would likely want one;
  not built here (out of scope for a runtime-strategy comparison).
- Memory growth over a long real session (beyond the 20 requests measured) is unconfirmed
  (`Memory.md`) — small in the sample taken, but the sample is short.
- Everything TE-002's own ADR draft already flagged as unresolved remains unresolved: CadQuery's
  patch is still not upstream, the `preview` command still only supports default parameters, and
  full desktop feature parity is completely unaddressed.

## Risks

Same list as `Conclusion.md`'s "Remaining risks" section.

## Migration strategy (sketch only, not a plan)

Would need, at minimum, before any real migration commitment: (1) everything TE-002's own ADR
draft already listed (upstream/wheel-pin the CadQuery patch, extend the contract to the full
`ZeroRodParameters` surface, scope full feature parity separately), plus (2) an idle-timeout policy
for the persistent engine, and (3) the completed human validation this document's sibling
(`HUMAN-VALIDATION.md`) is waiting on. None of these were attempted or are qualified by TE-002.1
alone to plan.

## Rollback strategy (sketch only)

None needed yet — nothing productive has changed. The existing PySide6 app remains the fallback
exactly as-is; TE-002.1, like every TE before it, never modified it. Within the PoC itself, the
onefile one-shot path (`requestPreviewOneShot`/`request_preview`) was deliberately kept working as
a secondary fallback rather than deleted, so reverting the *runtime strategy* specifically (without
reverting the whole architecture) remains possible without new work.

## Explicitly not decided by this draft

Whether to actually pursue this refinement, on what timeline, with what resourcing — same
disclaimer as TE-002's own ADR draft. This document records that the *technical* comparison has a
clear, evidence-backed answer (persistent + onedir); it does not answer the *product/roadmap*
question, and Gate E (the combined engineering + human verdict) is not yet complete.
