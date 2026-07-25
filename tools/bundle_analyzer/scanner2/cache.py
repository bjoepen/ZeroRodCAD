from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import FileFingerprint

CACHE_VERSION = 1


@dataclass(slots=True)
class ScanCache:
    """Small JSON cache for hashes and architecture metadata."""

    path: Path
    entries: dict[str, dict[str, Any]]
    hits: int = 0
    misses: int = 0

    @classmethod
    def load(cls, path: Path) -> ScanCache:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(path=path, entries={})
        if payload.get("version") != CACHE_VERSION:
            return cls(path=path, entries={})
        raw_entries = payload.get("entries", {})
        if not isinstance(raw_entries, dict):
            return cls(path=path, entries={})
        return cls(path=path, entries=raw_entries)

    def lookup(
        self,
        relative_path: str,
        fingerprint: FileFingerprint,
    ) -> dict[str, Any] | None:
        entry = self.entries.get(relative_path)
        if entry and entry.get("fingerprint") == fingerprint.cache_key:
            self.hits += 1
            return entry
        self.misses += 1
        return None

    def store(
        self,
        relative_path: str,
        fingerprint: FileFingerprint,
        *,
        sha256: str,
        is_macho: bool,
        architecture: tuple[str, ...],
    ) -> None:
        self.entries[relative_path] = {
            "fingerprint": fingerprint.cache_key,
            "sha256": sha256,
            "is_macho": is_macho,
            "architecture": list(architecture),
        }

    def prune(self, active_paths: set[str]) -> None:
        self.entries = {key: value for key, value in self.entries.items() if key in active_paths}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CACHE_VERSION,
            "entries": self.entries,
        }
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(self.path)
