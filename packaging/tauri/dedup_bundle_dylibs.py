#!/usr/bin/env python3
"""Build 022 M4 — productive dylib dedup post-bundle step.

Root cause (proven in docs/research/TE-002.2B-Tauri-Bundle-Optimization/
Optimization-B-Dylibs.md, reconfirmed productively in
docs/migration/BUILD-022-M4-PRODUCTIVE-PACKAGING.md "Discovery"):
PyInstaller's onedir COLLECT step already deduplicates identical binaries
via relative symlinks (e.g. OpenCASCADE's `_internal/libTKBin.7.9.3.dylib`
is a symlink to `_internal/OCP/.dylibs/libTKBin.7.9.3.dylib`). Tauri's
`bundle.resources` copy step dereferences every one of those symlinks while
copying `resources/zerorod-engine-onedir/` into the built `.app`'s
`Contents/Resources/`, turning each symlink back into a full real-file
copy. This script is the deterministic, reproducible fix: given the
pristine PyInstaller output (which still has the real symlinks) and the
built `.app`'s dereferenced copy, it restores each symlink — but only
after confirming, by SHA-256 (never by filename or size alone), that the
target file's current content still matches the symlink's resolved source
content. A pair that differs is left alone and reported as a loud failure,
not silently skipped — a real version difference is not a duplicate.

Adapted from tools/poc/tauri/dedup_bundle_dylibs.py (TE-002.2B's own proof
of this mechanism) for the productive Build 022 packaging path. Not an
import of that module — the PoC stays a standalone, untouched research
artifact; this is a separate, productive copy so the two can evolve
independently without productive packaging depending on `tools/poc/`.

Adds two things the PoC version didn't need: explicit idempotency
(a second run against already-relinked files is a documented no-op, not an
accidental side effect of the missing-target branch) and post-relink
symlink-safety verification (relative, resolves to a real file, stays
inside the bundle root — no absolute paths, no traversal outside it).

One documented exception found while validating this productively (not
present in TE-002.2B's own PoC measurement, which never exercised the full
`Python.framework` symlink chain): Tauri's resource copy does not just
dereference file symlinks, it also drops the `Python.framework/Versions/
Current` *directory* symlink entirely, leaving `Python.framework/Python`
(itself a symlink through `Versions/Current/Python`) unable to resolve in
the target tree even though the real file exists at `Versions/3.13/Python`.
This script safely reverts that one pair to a real-file copy rather than
leaving a broken symlink, and treats it as a known, expected exception
(`EXPECTED_UNSAFE_EXCEPTIONS` below) — the same "explain, don't force"
precedent TE-002.2A set for `libc++.1.0.dylib`'s genuine version
difference. Any *other* unsafe symlink is still a loud, strict failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Known, individually investigated, safe-to-leave-as-a-real-file exceptions.
# Each entry must have a one-line reason. Do not add to this list to make a
# strict-mode failure "go away" without first understanding *why* the
# symlink is unsafe — see Optimization-B-Dylibs.md's own discipline on this.
EXPECTED_UNSAFE_EXCEPTIONS: dict[str, str] = {
    "Python.framework/Python": (
        "Tauri's resource copy drops the Python.framework/Versions/Current "
        "directory symlink entirely (not just dereferences it), so the "
        "Versions/Current/Python path this symlink resolves through does "
        "not exist in the target tree, even though the real file exists at "
        "Versions/3.13/Python with identical content. Left as a real-file "
        "copy; costs ~4.8 MiB, not deduplicated."
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_safe_relative_symlink(link_path: Path, bundle_root: Path) -> tuple[bool, str]:
    """Verifies a symlink is relative, resolves to a real file, and stays
    inside `bundle_root` — never an absolute path, never a reference to the
    build environment (venv, repo checkout) or anything outside the bundle,
    so the bundle remains fully relocatable."""
    link_target = os.readlink(link_path)
    if os.path.isabs(link_target):
        return False, f"symlink target is an absolute path: {link_target!r}"
    resolved = (link_path.parent / link_target).resolve()
    try:
        resolved.relative_to(bundle_root.resolve())
    except ValueError:
        return False, f"symlink resolves outside the bundle root: {resolved}"
    if not resolved.is_file():
        return False, f"symlink target does not resolve to a real file: {resolved}"
    return True, ""


def dedup(
    source_internal: Path,
    target_internal: Path,
    *,
    bundle_root: Path,
    dry_run: bool = False,
) -> dict[str, object]:
    if not source_internal.is_dir():
        raise SystemExit(f"not found: {source_internal}")
    if not target_internal.is_dir():
        raise SystemExit(f"not found: {target_internal}")

    relinked: list[str] = []
    already_symlinked: list[str] = []
    skipped_different: list[str] = []
    skipped_missing_target: list[str] = []
    unsafe_symlinks: list[str] = []
    expected_exceptions_hit: list[str] = []
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

        if target_path.is_symlink():
            # Idempotency: a prior run (or a build that already preserved
            # the symlink) already fixed this one. Verify it's still safe
            # and move on — not an error, not re-done.
            safe, reason = _is_safe_relative_symlink(target_path, bundle_root)
            if not safe:
                unsafe_symlinks.append(f"{relative}: {reason}")
            else:
                already_symlinked.append(str(relative))
            continue

        if not target_path.is_file():
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
            safe, reason = _is_safe_relative_symlink(target_path, bundle_root)
            if not safe:
                # Restore what we had before rather than leave a broken
                # bundle. Most such cases are unreachable given the hash
                # check above, but at least one real, understood exception
                # exists (see EXPECTED_UNSAFE_EXCEPTIONS) — a loud, safe
                # failure for anything *not* on that list beats a silently
                # broken relocatable bundle either way.
                target_path.unlink()
                target_path.write_bytes(resolved_source.read_bytes())
                relative_str = str(relative)
                if relative_str in EXPECTED_UNSAFE_EXCEPTIONS:
                    expected_exceptions_hit.append(
                        f"{relative_str}: {EXPECTED_UNSAFE_EXCEPTIONS[relative_str]}"
                    )
                else:
                    unsafe_symlinks.append(f"{relative_str}: {reason} (relink reverted)")
                continue
        relinked.append(str(relative))
        bytes_reclaimed += size

    return {
        "relinked_count": len(relinked),
        "relinked_files": relinked,
        "already_symlinked_count": len(already_symlinked),
        "already_symlinked_files": already_symlinked,
        "skipped_different_content": skipped_different,
        "skipped_missing_target": skipped_missing_target,
        "unsafe_symlinks": unsafe_symlinks,
        "expected_exceptions_hit": expected_exceptions_hit,
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
        "(e.g. desktop/sidecar-dist/zerorod-engine/_internal) — read-only, "
        "used only to learn which files should be symlinks",
    )
    parser.add_argument(
        "target_internal",
        type=Path,
        help="the built .app's dereferenced copy, e.g. "
        "'<App>.app/Contents/Resources/zerorod-engine-onedir/_internal' "
        "— modified in place unless --dry-run",
    )
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=None,
        help="the .app bundle root, for symlink-safety verification "
        "(defaults to target_internal's ancestor 4 levels up, i.e. the "
        "'<App>.app' directory itself)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON only")
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="exit non-zero if any pair has mismatched content or an unsafe "
        "symlink was produced (default: on — this is a packaging-safety "
        "gate, not an advisory report)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_internal = args.source_internal.expanduser().resolve()
    target_internal = args.target_internal.expanduser().resolve()
    bundle_root = (
        args.bundle_root.expanduser().resolve() if args.bundle_root else target_internal.parents[3]
    )

    result = dedup(
        source_internal,
        target_internal,
        bundle_root=bundle_root,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        action = "would relink" if args.dry_run else "relinked"
        print(f"{action} {result['relinked_count']} files, {result['mib_reclaimed']} MiB reclaimed")
        if result["already_symlinked_count"]:
            print(
                f"{result['already_symlinked_count']} files already correctly "
                "symlinked (idempotent no-op)"
            )
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
        if result["expected_exceptions_hit"]:
            print(
                "expected, documented exceptions (see EXPECTED_UNSAFE_EXCEPTIONS): "
                f"{result['expected_exceptions_hit']}"
            )
        if result["unsafe_symlinks"]:
            print(
                f"UNSAFE SYMLINKS (reverted, bundle kept relocatable): {result['unsafe_symlinks']}"
            )

    if args.strict and (result["skipped_different_content"] or result["unsafe_symlinks"]):
        print(
            "FAILING: mismatched content or unsafe symlinks found — see above. "
            "Use a non-strict run only to investigate, never to ship.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
