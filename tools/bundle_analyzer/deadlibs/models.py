"""Domain models used by the dead-library analysis engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ConfidenceLevel(StrEnum):
    """Technical confidence assigned to an analysis finding."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingCategory(StrEnum):
    """Machine-readable classification of a library finding."""

    UNUSED = "unused"
    POSSIBLY_UNUSED = "possibly-unused"
    REFERENCED = "referenced"


class Recommendation(StrEnum):
    """User-facing action derived from evidence and confidence."""

    SAFE_REMOVE = "safe-remove"
    REVIEW = "review"
    KEEP = "keep"


class ReferenceKind(StrEnum):
    """Supported kinds of references to a bundled library."""

    MACHO = "macho"
    PYTHON_IMPORT = "python-import"
    PLUGIN_MANIFEST = "plugin-manifest"
    DYNAMIC_LOAD = "dynamic-load"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Reference:
    """A single piece of evidence that a library is used."""

    source: str
    target: str
    kind: ReferenceKind
    detail: str = ""


@dataclass(slots=True)
class UsageRecord:
    """Aggregated usage evidence for one logical library unit."""

    library_id: str
    references: list[Reference] = field(default_factory=list)
    unresolved_hints: list[str] = field(default_factory=list)

    @property
    def is_referenced(self) -> bool:
        return bool(self.references)


@dataclass(slots=True)
class LibraryUnit:
    """Logical library assembled from one or more bundle paths."""

    identifier: str
    paths: list[Path] = field(default_factory=list)
    size_bytes: int = 0

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("LibraryUnit.identifier must not be empty")
        if self.size_bytes < 0:
            raise ValueError("LibraryUnit.size_bytes must not be negative")
        self.paths = [Path(path) for path in self.paths]


@dataclass(slots=True)
class DeadLibraryFinding:
    """Analysis result for one logical library unit."""

    library: LibraryUnit
    usage: UsageRecord
    confidence: ConfidenceLevel
    category: FindingCategory
    recommendation: Recommendation
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DeadLibraryAnalysisResult:
    """Complete dead-library analysis result."""

    findings: list[DeadLibraryFinding] = field(default_factory=list)

    @property
    def removable_findings(self) -> list[DeadLibraryFinding]:
        return [
            finding
            for finding in self.findings
            if finding.recommendation is Recommendation.SAFE_REMOVE
        ]

    @property
    def potential_savings_bytes(self) -> int:
        return sum(finding.library.size_bytes for finding in self.removable_findings)
