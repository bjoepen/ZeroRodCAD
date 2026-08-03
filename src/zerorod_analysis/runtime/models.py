"""Immutable data models for runtime evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceStatus(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"


class EvidenceKind(StrEnum):
    PYTHON_MODULE = "python-module"
    NATIVE_EXTENSION = "native-extension"
    DYLIB = "dylib"
    FRAMEWORK = "framework"
    QT_PLUGIN = "qt-plugin"


@dataclass(frozen=True, slots=True)
class TraceEvidence:
    identity: str
    kind: EvidenceKind
    status: EvidenceStatus = EvidenceStatus.OBSERVED
    sources: tuple[str, ...] = ()
    event_count: int = 1
    bundle_relative_path: str | None = None
    details: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.identity:
            raise ValueError("TraceEvidence.identity must not be empty")
        if self.event_count < 1:
            raise ValueError("TraceEvidence.event_count must be positive")


@dataclass(frozen=True, slots=True)
class RuntimeTrace:
    schema: str
    build_id: str
    python_version: str
    platform: str
    started_at: str
    ended_at: str
    profile: str
    exit_status: str
    exit_code: int | None
    timed_out: bool
    incomplete: bool
    python_modules: tuple[TraceEvidence, ...] = ()
    native_extensions: tuple[TraceEvidence, ...] = ()
    loaded_libraries: tuple[TraceEvidence, ...] = ()
    qt_plugins: tuple[TraceEvidence, ...] = ()
    event_counts: tuple[tuple[str, int], ...] = ()
    error: str | None = None
