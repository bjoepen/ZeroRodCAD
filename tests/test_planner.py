from pathlib import Path

from tools.bundle_analyzer.models import BundleFile, DuplicateGroup
from tools.bundle_analyzer.planner import choose_canonical


def make(path: str) -> BundleFile:
    return BundleFile(
        path=Path(path),
        relative_path=path,
        size_bytes=1,
        sha256="x",
        inode=1,
        device=1,
        is_symlink=False,
    )


def test_frameworks_root_is_preferred() -> None:
    group = DuplicateGroup(
        sha256="x",
        size_bytes=1,
        files=(
            make("Contents/Resources/libx.dylib"),
            make("Contents/Frameworks/vtkmodules/__dot__dylibs/libx.dylib"),
            make("Contents/Frameworks/libx.dylib"),
        ),
    )
    assert str(choose_canonical(group)) == "Contents/Frameworks/libx.dylib"
