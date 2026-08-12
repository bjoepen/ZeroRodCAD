#!/usr/bin/env python3
"""TE-002.2B Optimization B — restore PyInstaller's own symlink dedup.

Root cause (found by direct inspection, not assumed): PyInstaller's onedir
COLLECT step for `tools/poc/tauri/sidecar-onedir.spec` already deduplicates
identical binaries via relative symlinks — e.g. `_internal/libTKBin.7.9.3.dylib`
is a symlink to `_internal/OCP/.dylibs/libTKBin.7.9.3.dylib`, and
`_internal/Python` / `_internal/Python.framework/Python` are a symlink chain
to the one real `Python.framework/Versions/3.13/Python` binary. Verified: the
standalone PyInstaller output at `experiments/te002-tauri/onedir-dist/zerorod-engine`
has zero duplicate bytes on disk for the whole 77-group set TE-002.2A found.

Tauri's `bundle.resources` copy step dereferences symlinks while copying
`resources/zerorod-engine-onedir/` into the built `.app`'s
`Contents/Resources/`, turning each symlink back into a full real-file copy
— that is where TE-002.2A's ~93.90 MiB of "duplicate" bytes actually comes
from; it is a Tauri-bundling artifact, not a PyInstaller packaging defect.

This script is the deterministic, reproducible packaging-time fix: given the
pristine PyInstaller source tree (which still has the real symlinks) and the
built `.app`'s dereferenced copy, it re-applies every symlink from the source
tree onto the target tree — but only after confirming, by hash, that the
target file's current (dereferenced) content still matches the symlink's
resolved target content in the source tree. A pair that differs is left
alone and reported (a genuine version difference, not a duplicate — see
TE-002.2A's `libc++.1.0.dylib` exception between `OCP/.dylibs/` and `casadi/`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dedup(
    source_internal: Path, target_internal: Path, *, dry_run: bool = False
) -> dict[str, object]:
    if not source_internal.is_dir():
        raise SystemExit(f"not found: {source_internal}")
    if not target_internal.is_dir():
        raise SystemExit(f"not found: {target_internal}")

    relinked: list[str] = []
    skipped_different: list[str] = []
    skipped_missing_target: list[str] = []
    bytes_reclaimed = 0

    for source_path in sorted(source_internal.rglob("*")):
        if not source_path.is_symlink():
            continue
        relative = source_path.relative_to(source_internal)
        link_target_relative = os.readlink(source_path)
        resolved_source = (source_path.parent / link_target_relative).resolve()
        if not resolved_source.is_file():
            continue

        target_path = target_internal / relative
        if not target_path.is_file() or target_path.is_symlink():
            skipped_missing_target.append(str(relative))
            continue
        if target_path.stat().st_size != resolved_source.stat().st_size:
            skipped_different.append(str(relative))
            continue
        if _sha256(target_path) != _sha256(resolved_source):
            skipped_different.append(str(relative))
            continue

        size = target_path.stat().st_size
        if not dry_run:
            target_path.unlink()
            target_path.symlink_to(link_target_relative)
        relinked.append(str(relative))
        bytes_reclaimed += size

    return {
        "relinked_count": len(relinked),
        "relinked_files": relinked,
        "skipped_different_content": skipped_different,
        "skipped_missing_target": skipped_missing_target,
        "bytes_reclaimed": bytes_reclaimed,
        "mib_reclaimed": round(bytes_reclaimed / 1024 / 1024, 2),
        "dry_run": dry_run,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source_internal",
        type=Path,
        help="pristine PyInstaller onedir output's _internal/ dir "
        "(e.g. experiments/te002-tauri/onedir-dist/zerorod-engine/_internal) "
        "— read-only, used only to learn which files should be symlinks",
    )
    parser.add_argument(
        "target_internal",
        type=Path,
        help="the built .app's dereferenced copy, e.g. "
        "'<App>.app/Contents/Resources/zerorod-engine-onedir/_internal' "
        "— modified in place unless --dry-run",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = dedup(
        args.source_internal.expanduser().resolve(),
        args.target_internal.expanduser().resolve(),
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        action = "would relink" if args.dry_run else "relinked"
        print(f"{action} {result['relinked_count']} files, {result['mib_reclaimed']} MiB reclaimed")
        if result["skipped_different_content"]:
            print(
                f"skipped {len(result['skipped_different_content'])} pairs with "
                f"different content (real differences, not duplicates): "
                f"{result['skipped_different_content']}"
            )
        if result["skipped_missing_target"]:
            print(
                f"skipped {len(result['skipped_missing_target'])} entries with no "
                f"matching real file in target: {result['skipped_missing_target']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
