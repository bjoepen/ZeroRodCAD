"""Privacy-preserving path normalization for runtime observations."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .models import EvidenceStatus


@dataclass(frozen=True, slots=True)
class NormalizedPath:
    identity: str
    status: EvidenceStatus
    bundle_relative_path: str | None = None


def _inside(path: Path, root: Path) -> Path | None:
    try:
        return path.relative_to(root)
    except ValueError:
        return None


def _redacted(label: str, raw: str) -> str:
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"<{label}>/{digest}"


def normalize_path(
    raw_path: str | os.PathLike[str],
    *,
    bundle_root: Path | None = None,
    home: Path | None = None,
    temp_roots: tuple[Path, ...] | None = None,
) -> NormalizedPath:
    """Return a stable identity without silently dropping an input path."""
    raw = os.fspath(raw_path).strip()
    if not raw:
        return NormalizedPath("<unresolved>/empty", EvidenceStatus.UNRESOLVED)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        safe = PurePosixPath(raw.replace("\\", "/")).as_posix()
        return NormalizedPath(safe, EvidenceStatus.UNRESOLVED)
    path = Path(os.path.normpath(path))
    if bundle_root is not None:
        relative = _inside(path, bundle_root.resolve(strict=False))
        if relative is not None:
            text = relative.as_posix()
            return NormalizedPath(text, EvidenceStatus.OBSERVED, text)
    text = path.as_posix()
    system_prefixes = ("/System/Library/", "/usr/lib/", "/Library/Apple/")
    if text.startswith(system_prefixes):
        return NormalizedPath(f"<system>{text}", EvidenceStatus.OBSERVED)
    effective_home = (home or Path.home()).resolve(strict=False)
    if _inside(path, effective_home) is not None:
        return NormalizedPath(_redacted("home", text), EvidenceStatus.UNRESOLVED)
    roots = temp_roots or (Path(tempfile.gettempdir()), Path("/tmp"), Path("/private/tmp"))
    if any(_inside(path, root.resolve(strict=False)) is not None for root in roots):
        return NormalizedPath(_redacted("temp", text), EvidenceStatus.UNRESOLVED)
    return NormalizedPath(_redacted("external", text), EvidenceStatus.UNRESOLVED)
