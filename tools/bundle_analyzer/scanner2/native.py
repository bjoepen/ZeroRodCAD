from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_MACHO_MAGICS = {
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xcf\xfa\xed\xfe",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xfe\xed\xfa\xce",
}


def is_macho_file(path: Path) -> bool:
    """Recognize Mach-O and universal binaries without invoking a subprocess."""

    if path.is_symlink() or not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            return handle.read(4) in _MACHO_MAGICS
    except OSError:
        return False


def architectures(path: Path, *, is_macho: bool) -> tuple[str, ...]:
    """Return architectures reported by lipo when available on macOS."""

    if not is_macho or shutil.which("lipo") is None:
        return ()
    process = subprocess.run(
        ["lipo", "-archs", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return ()
    return tuple(part for part in process.stdout.strip().split() if part)
