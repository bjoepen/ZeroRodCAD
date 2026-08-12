# ZeroRodCAD Documentation

The documentation is grouped by purpose instead of build order.

## Guides

- [macOS installation](guides/INSTALL_MACOS.md)
- [macOS packaging](guides/MACOS_PACKAGING.md)
- [dependency audit](guides/DEPENDENCY_AUDIT.md)
- [validation](guides/VALIDATION.md)
- [GitHub workflow](guides/GITHUB_WORKFLOW.md)

## Reference

- [Architecture](reference/ARCHITECTURE.md)
- [Project format](reference/PROJECT_FORMAT.md)

## Architecture decisions

Formal ADRs are stored under [`adr/`](adr/). The current desktop-architecture decision is
[ADR-022-001](adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md) (Status: Accepted) — Tauri v2 +
Rust process/IPC layer + persistent Python sidecar + Three.js, replacing PySide6/Qt + VTK as the
desktop target.

## Technology Evaluations (research)

Reproducible architecture/packaging research is stored under [`research/`](research/), one folder
per evaluation. The No-VTK / Tauri desktop-architecture evaluation phase (TE-001 through
TE-002.2B) is **COMPLETE**:

| Evaluation | Purpose | Result | Gate |
|---|---|---|---|
| [TE-001](research/TE-001-No-VTK/) | Can unmodified CadQuery run without VTK? | FAIL (eager `vtkmodules` import) | — |
| [TE-001.1](research/TE-001.1-CadQuery-NoVTK/) | Decouple CadQuery from VTK with a minimal patch | PASS | — |
| [TE-001.2](research/TE-001.2-NoVTK-Bundle/) | Prove the patch in a real production bundle | PASS | Gate C |
| [TE-002](research/TE-002-Tauri-ThreeJS/) | Tauri v2 + Python sidecar + Three.js, end to end | PASS | Gate D |
| [TE-002.1](research/TE-002.1-Sidecar-Runtime/) | Production-worthy sidecar runtime strategy | PASS (persistent + onedir) | Gate E-A |
| [TE-002.2A](research/TE-002.2A-Tauri-Bundle-Discovery/) | What is the Tauri bundle made of? | PASS (discovery only) | Gate F-A |
| [TE-002.2B](research/TE-002.2B-Tauri-Bundle-Optimization/) | Safely reduce the Tauri bundle | PASS (~280.27 MiB, −58.37%), human-validated | Gate F-B |

Each folder's own `Conclusion.md` (and, where applicable, `HUMAN-VALIDATION.md`) is authoritative;
this table is a pointer, not a duplicate of those reports. See
[`../ADR-022-001`](adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md) for how this evidence was
turned into a decision.

## Migration

The productive migration to the accepted Desktop 2.0 architecture is planned under
[`migration/`](migration/): [overview and build sequence](migration/README.md), and the current
next-step preparation document,
[Build 022 — Tauri Desktop Foundation](migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md) (prepared,
not started).

## Release history

Historical build notes are stored under [`releases/`](releases/).
Upgrade instructions are stored under [`upgrades/`](upgrades/).

## Documentation rule

New operational instructions belong in `guides/`. Stable technical facts belong
in `reference/`. Build-specific history belongs in `releases/`. Reproducible architecture/packaging
investigations belong in `research/`, one folder per evaluation. Formal architecture decisions
belong in `adr/`. Migration planning belongs in `migration/`.
