# Build 022 — Milestone 1: Tauri Desktop Foundation

Status: **COMPLETE**

## Objective

Establish the productive Tauri v2 project structure ZeroRodCAD Desktop 2.0 will actually ship —
distinct from the read-only `experiments/te002-tauri/` research PoC — with a real, buildable Rust
crate and TypeScript frontend, a working WebView-to-Rust IPC bridge, and the security boundary from
`ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md` already in place. M1 does not implement any
sidecar, process management, or preview logic — that is M2 (sidecar/Rust lifecycle) and M3
(Three.js preview).

## Why this was needed before M2

Build 022 / Milestone 2's own mandate assumes "Milestone 1 hat die produktive Tauri-v2-
Projektstruktur etabliert." No such structure existed anywhere in this repository or its branches
before this milestone (verified: no `feature/build022-m1-*` branch, commit, or `src-tauri/` outside
`experiments/te002-tauri/`). M1 was implemented first, as its own milestone with its own baseline,
so M2 has a real foundation to build the sidecar lifecycle on top of — not a placeholder.

## Decisions

- **Productive path: `desktop/`** (top-level, sibling to `experiments/`, `src/`, `tools/`) —
  `desktop/src-tauri/` (Rust crate) and `desktop/frontend/` (TypeScript + Vite). Kept structurally
  parallel to `experiments/te002-tauri/` (same `src-tauri/` + `frontend/` shape) so the proven PoC
  remains a legible reference, without being the same directory or being built upon directly.
- **Rust crate name:** `zerorod-desktop` (lib name `zerorod_desktop_lib`), Tauri identifier
  `dev.zerorodcad.desktop`, product name "ZeroRodCAD" — distinct from the PoC's
  `dev.zerorodcad.te0021` and from the legacy PySide6 app's `zerorodcad-desktop` Python package name
  (different ecosystems, no actual collision, chosen for human readability).
- **Frontend: TypeScript + Vite + Vitest**, not the PoC's plain JavaScript — Build 022 M2's own
  mandate explicitly requires a `tsc`/TypeScript check in its validation script and Definition of
  Done, so the productive frontend adopts TypeScript from M1 onward rather than retrofitting it
  later.
- **Icons:** the PoC's existing generated icon set (`experiments/te002-tauri/src-tauri/icons/`) was
  copied as a bootstrap placeholder so the app can build and bundle today. This is **not** final
  branding — replacing it with real ZeroRodCAD artwork (an existing `assets/macos/ZeroRodCAD.icns`
  exists for the legacy app and could inform it) is deferred to a later milestone, not blocking for
  a foundation whose own UI has no visual identity requirements yet.
- **Tauri build-hook cwd (undocumented behavior found during this milestone):** Tauri v2's CLI runs
  `beforeDevCommand`/`beforeBuildCommand` with cwd set to the **app root** (the directory containing
  `src-tauri/`, i.e. `desktop/`) — not the directory containing `tauri.conf.json` itself. The PoC's
  `../frontend`-relative command works there only because of how `tauri dev`/`build` happened to be
  invoked in that evaluation; testing this productively surfaced that the correct relative path from
  the app root is `frontend`, not `../frontend`. `desktop/src-tauri/tauri.conf.json` uses
  `"beforeBuildCommand": "npm --prefix frontend run build"` accordingly — confirmed working with a
  real `tauri build` (see "Real app validation").

## What M1 implements

- `desktop/src-tauri/`: a minimal Tauri v2 app (`tauri = "2"`, no plugins yet — `tauri-plugin-shell`
  is deliberately not added until M2 actually needs it for sidecar process spawning), one command
  (`app_info`) returning `{name, version, build, milestone}`, a restrictive capability
  (`core:default` only, no shell/process/filesystem permission — matches
  `ADR-022-001`'s security boundary) and the same restrictive CSP the PoC proved:
  `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;
  connect-src 'self' ipc: http://ipc.localhost`.
- `desktop/frontend/`: a TypeScript + Vite app with a small, renderer-independent status-panel
  module (`status.ts`, unit-tested without any DOM/Tauri dependency) and `main.ts`, which calls
  `app_info` through `@tauri-apps/api/core`'s `invoke()` and renders five status rows: Desktop
  shell (READY), Rust bridge (READY once `app_info` succeeds, ERROR otherwise), and three rows
  correctly marked `NOT_IMPLEMENTED` for what M1 does not touch — Python sidecar (M2), CAD engine
  (M2), 3D preview (M3).

## Explicitly not implemented in M1

- Any sidecar process, Python integration, or `zerorod-sidecar/v1`/`zerorod-mesh/v1` handling (M2).
- Any Three.js rendering or preview data consumption (M3).
- Parameter UI, export UI, feature parity, PySide6 removal (Builds 023–026, per
  `docs/migration/README.md`).

## Security boundary

- WebView capability: `core:default` only (`desktop/src-tauri/capabilities/main-capability.json`)
  — no shell, process, or filesystem permission.
- Rust dependencies: `tauri`, `serde` only. No `tauri-plugin-shell` yet — there is nothing to spawn.
- CSP: unchanged from the TE-002/TE-002.1/TE-002.2B baseline (see above).

## Tests

- Rust: 1 unit test (`commands::tests::app_info_reports_build_022_m1`) — `cargo test` PASS.
- Frontend: 6 unit tests (`status.test.ts`, covering `statusCssClass` mapping, row rendering, and
  HTML-escaping of backend-provided text) — `vitest run` PASS.

## Validation performed

All commands run for real in this milestone, not simulated:

| Check | Result |
|---|---|
| `cargo check` (`desktop/src-tauri`) | PASS |
| `cargo test` | PASS (1/1) |
| `cargo fmt --check` | PASS |
| `cargo clippy --all-targets -- -D warnings` | PASS (0 warnings) |
| `npm run typecheck` (`tsc --noEmit`) | PASS |
| `npm run test` (`vitest run`) | PASS (6/6) |
| `npm run build` (`tsc && vite build`) | PASS |

## Real app validation

A real debug build was produced with the actual Tauri CLI (`tauri build --debug`, not a mocked or
partial build) and launched as a real `.app`:

```text
desktop/src-tauri/target/debug/bundle/macos/ZeroRodCAD.app
```

Observed directly (screenshot taken and inspected during this milestone, not assumed): the window
opens with the title "ZeroRodCAD Desktop", and the foundation UI renders all five status rows
correctly — critically, **Rust bridge shows READY with real data** (`ZeroRodCAD Desktop 0.1.0
(M1)`), proving the `invoke("app_info")` round trip actually works through a real WebView, not just
in a headless test. The app was then quit (`osascript ... quit`, backed up by `pkill`), and a
process check confirmed **0 remaining `zerorod-desktop`/`ZeroRodCAD` processes** — clean shutdown,
no orphan, consistent with what M2's sidecar lifecycle work will need to preserve for the
persistent Python process too.

## Read-only references confirmed untouched

- `experiments/te002-tauri/`: not modified — `desktop/` is a new, separate tree.
- Legacy PySide6 app (`src/zerorodcad_desktop/`): not modified.

## Next milestone

**Build 022 / Milestone 2 — Productive Sidecar & Rust Lifecycle.** M1 gives the productive desktop
app a working shell and IPC bridge; M2 gives it a real, persistent Python 3.13 sidecar and the Rust
process-lifecycle management around it.
