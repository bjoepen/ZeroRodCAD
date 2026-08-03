from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class BundleSection(StrEnum):
    """Logical location of a file inside a macOS application bundle."""

    MACOS = "MacOS"
    FRAMEWORKS = "Frameworks"
    RESOURCES = "Resources"
    PLUGINS = "PlugIns"
    PYSIDE = "PySide6"
    QT = "Qt"
    VTK = "VTK"
    OCP = "OCP"
    CASADI = "casadi"
    PYTHON = "Python"
    EXECUTABLES = "Executables"
    OTHER = "Other"


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    """Persistent identity used to decide whether a file must be rehashed."""

    size_bytes: int
    modified_ns: int
    inode: int
    device: int

    @property
    def cache_key(self) -> str:
        return ":".join(
            str(value)
            for value in (
                self.size_bytes,
                self.modified_ns,
                self.inode,
                self.device,
            )
        )


@dataclass(frozen=True, slots=True)
class BundleFile:
    """Normalized record for one file or symbolic link in a bundle."""

    path: Path
    relative_path: str
    filename: str
    extension: str
    size_bytes: int
    sha256: str
    modified_ns: int
    inode: int
    device: int
    is_symlink: bool
    symlink_target: str | None
    section: BundleSection
    is_macho: bool
    architecture: tuple[str, ...]

    @property
    def fingerprint(self) -> FileFingerprint:
        return FileFingerprint(
            size_bytes=self.size_bytes,
            modified_ns=self.modified_ns,
            inode=self.inode,
            device=self.device,
        )
