from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from .cache import ScanCache
from .classification import classify_section
from .database import BundleDatabase
from .filters import ScanFilter
from .models import BundleFile, FileFingerprint
from .native import architectures, is_macho_file


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(slots=True)
class Scanner:
    """Build a complete and cacheable index of a macOS .app bundle."""

    cache_name: str = "scanner2-cache.json"

    def scan(
        self,
        app_bundle: Path,
        *,
        cache_dir: Path | None = None,
        use_cache: bool = True,
        scan_filter: ScanFilter | None = None,
    ) -> BundleDatabase:
        app_bundle = app_bundle.expanduser().resolve()
        contents = app_bundle / "Contents"
        if app_bundle.suffix != ".app" or not contents.is_dir():
            raise ValueError(f"Kein gültiges macOS-App-Bundle: {app_bundle}")

        selected_cache_dir = cache_dir or Path(".cache/bundle-analyzer")
        cache_path = selected_cache_dir / self.cache_name
        cache = ScanCache.load(cache_path) if use_cache else ScanCache(cache_path, {})

        records: list[BundleFile] = []
        active_paths: set[str] = set()
        directory_count = 0

        for current_root, directories, filenames in os.walk(
            contents,
            followlinks=False,
        ):
            directories.sort()
            filenames.sort()
            directory_count += len(directories)
            current = Path(current_root)

            for filename in filenames:
                path = current / filename
                relative_path = path.relative_to(app_bundle).as_posix()
                active_paths.add(relative_path)
                item = self._inspect(path, relative_path, cache)
                if scan_filter is None or scan_filter.matches(item):
                    records.append(item)

            for directory in directories:
                path = current / directory
                if not path.is_symlink():
                    continue
                relative_path = path.relative_to(app_bundle).as_posix()
                active_paths.add(relative_path)
                item = self._inspect(path, relative_path, cache)
                if scan_filter is None or scan_filter.matches(item):
                    records.append(item)

        if use_cache:
            cache.prune(active_paths)
            cache.save()

        return BundleDatabase(
            root=app_bundle,
            files=tuple(sorted(records, key=lambda item: item.relative_path)),
            directory_count=directory_count,
            cache_hits=cache.hits,
            cache_misses=cache.misses,
        )

    def _inspect(
        self,
        path: Path,
        relative_path: str,
        cache: ScanCache,
    ) -> BundleFile:
        is_symlink = path.is_symlink()
        symlink_target = os.readlink(path) if is_symlink else None
        stat = path.lstat() if is_symlink else path.stat()
        fingerprint = FileFingerprint(
            size_bytes=stat.st_size,
            modified_ns=stat.st_mtime_ns,
            inode=stat.st_ino,
            device=stat.st_dev,
        )
        cached = cache.lookup(relative_path, fingerprint)

        if cached is None:
            macho = is_macho_file(path)
            arch = architectures(path, is_macho=macho)
            digest = self._symlink_digest(symlink_target) if is_symlink else sha256_file(path)
            cache.store(
                relative_path,
                fingerprint,
                sha256=digest,
                is_macho=macho,
                architecture=arch,
            )
        else:
            digest = str(cached["sha256"])
            macho = bool(cached.get("is_macho", False))
            arch = tuple(str(value) for value in cached.get("architecture", []))

        return BundleFile(
            path=path,
            relative_path=relative_path,
            filename=path.name,
            extension=path.suffix.casefold(),
            size_bytes=stat.st_size,
            sha256=digest,
            modified_ns=stat.st_mtime_ns,
            inode=stat.st_ino,
            device=stat.st_dev,
            is_symlink=is_symlink,
            symlink_target=symlink_target,
            section=classify_section(relative_path, is_macho=macho),
            is_macho=macho,
            architecture=arch,
        )

    @staticmethod
    def _symlink_digest(target: str | None) -> str:
        value = target or ""
        return hashlib.sha256(f"symlink:{value}".encode()).hexdigest()
