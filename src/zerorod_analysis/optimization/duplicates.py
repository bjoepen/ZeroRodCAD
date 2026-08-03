from __future__ import annotations

from collections import defaultdict

from ..models import BundleFile, DuplicateGroup


def duplicate_groups(files: list[BundleFile]) -> list[DuplicateGroup]:
    grouped: dict[str, list[BundleFile]] = defaultdict(list)
    for item in files:
        grouped[item.sha256].append(item)

    result = [
        DuplicateGroup(
            sha256=sha256,
            size_bytes=items[0].size_bytes,
            files=tuple(items),
        )
        for sha256, items in grouped.items()
        if len(items) > 1
    ]
    return sorted(result, key=lambda group: group.redundant_bytes, reverse=True)
