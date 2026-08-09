# TE-002.2B — Optimization A: Remove the Onefile Sidecar Fallback

## Change

Removed `"externalBin": ["binaries/zerorod-engine"]` from
`experiments/te002-tauri/src-tauri/tauri.conf.json`'s `bundle` block. Nothing else touched —
`sidecar.rs`'s `request_preview` command and `sidecar.js`'s `requestPreviewOneShot` export are
left in place (dead-but-callable code, not removed from history or wiring), per the mandate's
"only remove from active bundle config" instruction. Verified this is safe by reading
`sidecar.rs::request_preview`: `app.shell().sidecar(SIDECAR_NAME)` returns a `Result`, mapped to a
structured `PreviewError::new("sidecar_missing", ...)` — no panic if the externalBin can't be
resolved, just a clean error if that dead code path is ever invoked. The primary, UI-wired path is
`persistent_preview` (`sidecar.js` line 38) — `requestPreviewOneShot` is exported but not called
from `index.html`'s actual button flow (already documented in `sidecar.js`'s own comments as
"reference/fallback, not removed").

## Isolated measurement (onefile removed, dylib dedup *not* yet applied)

| | Bytes | MiB | Files |
|---|---:|---:|---:|
| Baseline | 706,051,017 | 673.34 | 372 |
| A only | 564,019,881 | 537.89 | 371 |
| **Savings** | **142,031,136** | **135.45** | **1** |

Matches TE-002.2A's predicted onefile size (135.45 MiB) almost exactly — confirms the onefile
copy was the only thing removed, no side effects.

## Validation

- `cargo check` / `cargo build --release`: compiles cleanly with `externalBin` absent (confirms no
  compile-time dependency on it).
- `cargo test`: 17/17 pass (15 unit + 2 onedir integration) — unchanged from TE-002.1.
- Onedir persistent protocol (the only remaining, UI-wired path) still fully functional: see
  `Runtime-Validation.md`.
- `Contents/MacOS/` now contains exactly one file (`te002-tauri`) instead of two.

## Accepted

Onefile fallback removal is **ACCEPTED**. Real, measured, isolated savings of 135.45 MiB with zero
functional impact on the persistent-onedir path TE-002.1 already chose as the sole production
strategy.
