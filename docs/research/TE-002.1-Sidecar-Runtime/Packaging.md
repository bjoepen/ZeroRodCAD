# TE-002.1 — Packaging / Deployment Footprint

Measured via `_dir_size_and_count()` (stdlib `os.walk`) against the actual built PyInstaller
artifact for each variant, not estimated.

| Variant | Packaging | Disk size | File count |
|---|---|---|---|
| A / C (onefile) | single self-extracting executable | 135.45 MiB (142,032,320 / 142,031,664 bytes — the 656-byte difference between A's and C's builds is normal build-to-build variation, not a packaging difference) | 1 |
| B / D (onedir) | executable + `_internal/` support tree | 524.74 MiB (550,232,901 bytes) | 368 |

Onedir is ~3.9× larger on disk and ships hundreds of loose files instead of one, because nothing
is compressed/bundled into a single self-extracting archive — every dependency (OCP, `numba`,
`scipy`, `numpy`, etc.) sits as its own file tree. Onefile trades that disk/file-count cost for
the self-extraction cost paid at every cold start (`Performance.md`).

## What this means for the actual app bundle

TE-002.1's built test app (`Packaging` continued in `Results.md`/`Conclusion.md`) kept **both**
artifacts — the onefile sidecar via Tauri's `externalBin` (the original TE-002 one-shot fallback
path, `request_preview`/`requestPreviewOneShot`, still callable) and the onedir sidecar via a
`bundle.resources` entry (the new default persistent path, `persistent_preview`). This is why the
final `.app` bundle (674 MB total) is larger than either variant's artifact alone — it is not a
production packaging decision, it's a technology-evaluation artifact that intentionally kept both
code paths available for comparison and fallback. A production build would ship only the chosen
variant's artifact, not both.

## Tauri packaging mechanism used for onedir (a real constraint, solved)

Tauri's `bundle.externalBin` only supports single-file sidecars (it requires the
`<name>-<target-triple>` naming convention and copies exactly one file). A whole directory tree
like onedir's output can't be declared that way. Solved instead via `bundle.resources` (an
object-form mapping copying `resources/zerorod-engine-onedir/` → `zerorod-engine-onedir/` inside
the bundle's `Contents/Resources/`), resolved at runtime via
`app.path().resolve("zerorod-engine-onedir/zerorod-engine", BaseDirectory::Resource)`, and spawned
via `app.shell().command(path)` — the same underlying `Command`/`CommandChild` types
`ShellExt::sidecar()` returns, just not gated by the externalBin naming convention. Verified to
compile, pass all tests, and work when driven from real Rust code (not just a shell) via
`experiments/te002-tauri/src-tauri/tests/onedir_variant.rs`.
