from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BundleFile:
    path: Path
    relative_path: str
    size_bytes: int
    sha256: str
    inode: int
    device: int
    is_symlink: bool


@dataclass(frozen=True)
class DuplicateGroup:
    sha256: str
    size_bytes: int
    files: tuple[BundleFile, ...]

    @property
    def redundant_bytes(self) -> int:
        return self.size_bytes * max(0, len(self.files) - 1)
