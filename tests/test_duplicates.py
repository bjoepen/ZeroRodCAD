from pathlib import Path

from tools.bundle_analyzer.duplicates import duplicate_groups
from tools.bundle_analyzer.models import BundleFile


def item(name: str, digest: str, size: int = 10) -> BundleFile:
    return BundleFile(
        path=Path(name),
        relative_path=name,
        size_bytes=size,
        sha256=digest,
        inode=1,
        device=1,
        is_symlink=False,
    )


def test_duplicate_groups_detect_byte_identical_files() -> None:
    groups = duplicate_groups(
        [
            item("a.dylib", "same"),
            item("b.dylib", "same"),
            item("c.dylib", "other"),
        ]
    )
    assert len(groups) == 1
    assert groups[0].redundant_bytes == 10
