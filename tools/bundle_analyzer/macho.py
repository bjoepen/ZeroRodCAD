from __future__ import annotations

import subprocess
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .scanner2 import BundleDatabase


@dataclass(frozen=True, slots=True)
class MachOBinary:
    relative_path: str
    macho_id: str | None
    raw_dependencies: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    edges: dict[str, tuple[str, ...]]
    external_dependencies: dict[str, tuple[str, ...]]
    reverse_edges: dict[str, tuple[str, ...]]

    def reachable_from(self, roots: Iterable[str]) -> frozenset[str]:
        reachable: set[str] = set()
        queue = deque(root for root in roots if root in self.edges)
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            queue.extend(self.edges.get(current, ()))
        return frozenset(reachable)


def otool_dependencies(path: Path) -> list[str]:
    process = subprocess.run(
        ["otool", "-L", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return []
    return [
        line.strip().split(" (compatibility", 1)[0]
        for line in process.stdout.splitlines()[1:]
        if line.strip()
    ]


def macho_id(path: Path) -> str | None:
    process = subprocess.run(
        ["otool", "-D", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return None
    lines = [line.strip() for line in process.stdout.splitlines()[1:] if line.strip()]
    return lines[0] if lines else None


class MachOAnalyzer:
    def analyze(self, database: BundleDatabase) -> tuple[MachOBinary, ...]:
        binaries = [item for item in database.files if item.is_macho]
        return tuple(
            MachOBinary(
                relative_path=item.relative_path,
                macho_id=macho_id(item.path),
                raw_dependencies=tuple(otool_dependencies(item.path)),
            )
            for item in sorted(binaries, key=lambda value: value.relative_path)
        )


def _candidate_suffixes(raw: str) -> tuple[str, ...]:
    normalized = raw.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    suffixes: list[str] = []
    for marker in ("Frameworks", "PlugIns", "MacOS", "Resources"):
        if marker in parts:
            suffixes.append("/".join(parts[parts.index(marker) :]))
    if ".framework/" in normalized:
        framework_root, framework_suffix = normalized.split(".framework/", 1)
        framework_name = framework_root.split("/")[-1]
        suffixes.append(f"{framework_name}.framework/{framework_suffix}")
    suffixes.append(PurePosixPath(normalized).name)
    return tuple(dict.fromkeys(suffixes))


def _resolve_dependency(raw: str, loader: str, known_paths: set[str]) -> str | None:
    loader_dir = PurePosixPath(loader).parent
    candidates: list[str] = []
    if raw.startswith("@loader_path/"):
        candidates.append(str(loader_dir / raw.removeprefix("@loader_path/")))
    elif raw.startswith("@executable_path/"):
        executable_root = PurePosixPath("Contents/MacOS")
        candidates.append(str(executable_root / raw.removeprefix("@executable_path/")))
    elif raw.startswith("@rpath/"):
        relative = raw.removeprefix("@rpath/")
        candidates.extend((f"Contents/Frameworks/{relative}", relative))
    elif not raw.startswith("/"):
        candidates.append(raw)

    normalized_candidates = [str(PurePosixPath(candidate)) for candidate in candidates]
    for candidate in normalized_candidates:
        if candidate in known_paths:
            return candidate

    for suffix in _candidate_suffixes(raw):
        matches = sorted(path for path in known_paths if path.endswith(suffix))
        if len(matches) == 1:
            return matches[0]
    return None


def build_dependency_graph(
    binaries: Iterable[MachOBinary], bundle_root: Path | None = None
) -> DependencyGraph:
    del bundle_root
    items = tuple(binaries)
    known_paths = {item.relative_path for item in items}
    id_index = {item.macho_id: item.relative_path for item in items if item.macho_id is not None}
    edges: dict[str, tuple[str, ...]] = {}
    external: dict[str, tuple[str, ...]] = {}
    reverse: dict[str, list[str]] = {path: [] for path in known_paths}

    for item in items:
        resolved: list[str] = []
        unresolved: list[str] = []
        for dependency in item.raw_dependencies:
            target = id_index.get(dependency) or _resolve_dependency(
                dependency, item.relative_path, known_paths
            )
            if target is None:
                unresolved.append(dependency)
            elif target != item.relative_path:
                resolved.append(target)
                reverse.setdefault(target, []).append(item.relative_path)
        edges[item.relative_path] = tuple(sorted(set(resolved)))
        external[item.relative_path] = tuple(sorted(set(unresolved)))

    return DependencyGraph(
        edges=edges,
        external_dependencies=external,
        reverse_edges={key: tuple(sorted(set(values))) for key, values in reverse.items()},
    )
