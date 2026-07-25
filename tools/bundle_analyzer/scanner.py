from __future__ import annotations

from pathlib import Path

from .hashing import sha256_file
from .models import BundleFile

DEFAULT_PATTERNS = ("*.dylib", "*.so")


def scan_bundle(app_bundle: Path, patterns: tuple[str, ...] = DEFAULT_PATTERNS) -> list[BundleFile]:
    app_bundle = app_bundle.resolve()
    contents = app_bundle / "Contents"
    if not contents.is_dir():
        raise ValueError(f"Kein gültiges macOS-App-Bundle: {app_bundle}")

    paths: set[Path] = set()
    for pattern in patterns:
        paths.update(path for path in contents.rglob(pattern) if path.is_file())

    records: list[BundleFile] = []
    for path in sorted(paths):
        stat = path.stat()
        records.append(
            BundleFile(
                path=path,
                relative_path=str(path.relative_to(app_bundle)),
                size_bytes=stat.st_size,
                sha256=sha256_file(path),
                inode=stat.st_ino,
                device=stat.st_dev,
                is_symlink=path.is_symlink(),
            )
        )
    return records
