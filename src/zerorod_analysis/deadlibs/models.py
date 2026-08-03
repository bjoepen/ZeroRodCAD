"""Domain models used by the dead-library analysis engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..advisor import Advice, BundleHealth
    from ..macho import DependencyGraph, MachOBinary
    from ..metrics import PipelineMetrics
    from ..scanner import BundleDatabase


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingCategory(StrEnum):
    FRAMEWORK = "framework"
    DYLIB = "dylib"
    PYTHON_PACKAGE = "python-package"
    RESOURCE = "resource"
    DUPLICATE = "duplicate"
    REFERENCED = "referenced"
    UNUSED = "unused"
    POSSIBLY_UNUSED = "possibly-unused"


class Recommendation(StrEnum):
    SAFE_REMOVE = "safe-remove"
    REVIEW = "review"
    KEEP = "keep"


class ReferenceKind(StrEnum):
    MACHO = "macho"
    MACHO_DEPENDENCY = "macho-dependency"
    PYTHON_IMPORT = "python-import"
    PLUGIN_MANIFEST = "plugin-manifest"
    DYNAMIC_LOAD = "dynamic-load"
    DYNAMIC_LOAD_HINT = "dynamic-load-hint"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Reference:
    source: str
    target: str
    kind: ReferenceKind
    detail: str = ""


@dataclass(slots=True)
class UsageRecord:
    library_id: str
    references: list[Reference] = field(default_factory=list)
    unresolved_hints: list[str] = field(default_factory=list)

    @property
    def is_referenced(self) -> bool:
        return bool(self.references)

    @property
    def dynamic_hints(self) -> tuple[Reference, ...]:
        dynamic_kinds = {ReferenceKind.DYNAMIC_LOAD, ReferenceKind.DYNAMIC_LOAD_HINT}
        return tuple(reference for reference in self.references if reference.kind in dynamic_kinds)

    @property
    def static_references(self) -> tuple[Reference, ...]:
        dynamic_kinds = {ReferenceKind.DYNAMIC_LOAD, ReferenceKind.DYNAMIC_LOAD_HINT}
        return tuple(
            reference for reference in self.references if reference.kind not in dynamic_kinds
        )


@dataclass(slots=True)
class LibraryUnit:
    identifier: str
    paths: list[Path] = field(default_factory=list)
    size_bytes: int = 0
    category: FindingCategory = FindingCategory.DYLIB

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("LibraryUnit.identifier must not be empty")
        if self.size_bytes < 0:
            raise ValueError("LibraryUnit.size_bytes must not be negative")
        self.paths = [Path(path) for path in self.paths]


@dataclass(slots=True)
class DeadLibraryFinding:
    library: LibraryUnit
    usage: UsageRecord
    confidence: ConfidenceLevel
    category: FindingCategory
    recommendation: Recommendation
    reasons: list[str] = field(default_factory=list)
    risk_score: int | None = None


@dataclass(slots=True)
class DeadLibraryAnalysisResult:
    findings: list[DeadLibraryFinding] = field(default_factory=list)
    bundle_root: Path | None = None
    total_bundle_size_bytes: int = 0
    database: BundleDatabase | None = None
    macho_binaries: tuple[MachOBinary, ...] | None = None
    dependency_graph: DependencyGraph | None = None
    advisor_results: tuple[Advice, ...] | None = None
    bundle_health: BundleHealth | None = None
    analysis_metrics: PipelineMetrics | None = None

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

    @property
    def used_findings(self) -> list[DeadLibraryFinding]:
        return [
            finding for finding in self.findings if finding.recommendation is Recommendation.KEEP
        ]
