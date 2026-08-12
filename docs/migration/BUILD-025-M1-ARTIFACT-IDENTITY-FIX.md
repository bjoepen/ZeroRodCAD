# Build 025 / Milestone 1 — Artifact Identity Fix

The Project Owner opened the first `ZeroRodCAD-Build025-M1.app` human-validation artifact and
found it still visibly labeled `Build 024 — Milestone 2` in the main window, immediately below the
`ZeroRodCAD Desktop 2.0` title. Human Validation was correctly withheld pending clarification.

## Root cause

**Category: `HARDCODED_FRONTEND_STRING`, duplicated against a second, independent source.**

`desktop/frontend/src/main.ts` built its DOM shell with a literal, milestone-specific subtitle:

```ts
<p class="subtitle">Build 024 — Milestone 2: Native Save Dialog &amp; Export Controls</p>
```

introduced during Build 024 M2 (commit `31d1d11`) and never updated since — not in Build 024 M3,
not in M4, not in Build 025 Discovery, not in Build 025 M1's own engineering pass. It was
completely independent of the app's *actual* build/milestone identity source,
`desktop/src-tauri/src/commands.rs`'s `app_info()` Tauri command (`AppInfo { name, version, build,
milestone }`), which was *itself* also stale (`build: "022"`, `milestone: "M3"` — left over from
Build 022 M3, equally never bumped in any later milestone) but rendered separately, into the status
panel's "Rust bridge" row (`${info.name} ${info.version} (${info.milestone})`), where it read
`(M3)` — not the exact string the Project Owner reported, but the same underlying defect class:
**two independently hardcoded, independently stale identity strings, in two different UI
locations, agreeing with neither each other nor reality.**

- Source file: `desktop/frontend/src/main.ts`
- Source line: 27 (the static subtitle, the exact reported defect)
- Contributing/related staleness: `desktop/src-tauri/src/commands.rs`, lines 28-29 (`app_info()`'s
  `build`/`milestone` fields — a second, independently stale copy, visible elsewhere in the same
  UI)

Not a `BUILD_METADATA`, `PACKAGE_VERSION`, `TAURI_CONFIG`, `RUST_CONSTANT`-as-single-source,
`STALE_GENERATED_ASSET`, or `CACHED_FRONTEND` issue: `tauri.conf.json`'s `version` (`0.1.0`) was
never wrong or displayed; nothing was cached (a full rebuild reproduced the identical stale text,
since it was source, not a build artifact left over from a prior run); no code-generation step was
involved.

## Product decision

Per the mandate's own preference (normal product UI should not permanently display internal
engineering milestone labels): the milestone-specific subtitle is **removed** from the main
window's top-level UI entirely, rather than corrected to a new hardcoded "Build 025 — Milestone 1"
string that would just as certainly go stale again at the start of M2. The `<h1>ZeroRodCAD Desktop
2.0</h1>` title alone is timeless and needs no further per-milestone text.

The precise build/milestone identity `ZeroRodCAD-Build025-M1.app`'s Human Validation checklist asks
for is still available — no new UI was built for this. The existing status panel's "Rust bridge"
row (already present since Build 022 M1, already populated from a real IPC round trip in `init()`)
now shows it: `${info.name} ${info.version} — Build ${info.build} ${info.milestone}`, e.g.
`ZeroRodCAD Desktop 0.1.0 — Build 025 M1`.

## Single source of truth (§6)

`commands.rs`'s `app_info()` — already the app's one real "app metadata" endpoint (Build 022 M1) —
is now the **only** place `build`/`milestone` are ever written. `main.ts` reads both fields from
one live `fetchAppInfo()` call; nothing else in the frontend hardcodes either value. A future
milestone updates exactly one pair of string literals, in one file
(`desktop/src-tauri/src/commands.rs`), for the identity to be correct everywhere it's shown — no
second copy left to drift.

## Fix

- `commands.rs`: `app_info()`'s `build`/`milestone` updated from the stale `"022"`/`"M3"` to
  `"025"`/`"M1"`, with a doc comment recording why this pair must never be duplicated elsewhere
  again.
- `main.ts`: the hardcoded `<p class="subtitle">...</p>` line deleted; the "Rust bridge" status row
  now renders `Build ${info.build} ${info.milestone}` from the live `app_info()` response.
- `style.css`: the now-unused `.subtitle` rule removed; `h1`'s bottom margin restored to a normal
  value (previously tightened to sit close to the now-deleted subtitle).

## Regression protection (§7)

- `commands.rs`: `app_info_reports_build_025_m1` (pins the current, correct pair) and
  `app_info_never_reports_a_stale_024_m2_pair` (a direct, permanent guard against this exact
  regression, independent of whatever the "current" pair becomes in the future).
- `scripts/validate-build025-m1.sh`, new section "Visible build/milestone identity": checks the
  *source* (`commands.rs` has the current pair and not the stale one; `main.ts` no longer hardcodes
  a second `Build 0NN ... Milestone/MN` string and only ever interpolates
  `${info.build} ${info.milestone}`) and, separately, the *freshly built artifacts* (the compiled
  frontend bundle contains no visible `024 — Milestone 2` / `024 M2` text; the compiled Rust binary
  contains the current `025`/`M1` strings and not the stale `024`/`M2` pair as adjacent
  `strings(1)` output — approximating what `app_info()`'s compiled string literals actually look
  like in the binary).

## Identity proof (this fix's own fresh build)

See the accompanying Artifact Identity Fix Report (delivered as this session's final message) for
the actual measured frontend-asset hash, binary hash, and `strings(1)` search results against the
freshly rebuilt `ZeroRodCAD-Build025-M1.app` — not asserted here ahead of that rebuild.

## Scope discipline

Nothing else about Build 025 M1's project-persistence functionality was touched. No M2 work
(Diagnostics relocation, native menus, automatic initial preview, startup-failure UX) was started.
