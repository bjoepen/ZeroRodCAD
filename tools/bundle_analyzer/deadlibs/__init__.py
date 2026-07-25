"""Public API for Build 019.3 dead-library analysis."""

from .aggregate import aggregate_library_units
from .analyzer import DeadLibraryAnalyzer
from .confidence import assess_usage, classify_confidence
from .models import (
    ConfidenceLevel,
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    FindingCategory,
    LibraryUnit,
    Recommendation,
    Reference,
    ReferenceKind,
    UsageRecord,
)
from .resolver import DeadLibraryResolver, resolve_usage
from .size import SizeAnalysis, SizeSummary, compute_savings, summarize_sizes

__all__ = [
    "ConfidenceLevel",
    "DeadLibraryAnalysisResult",
    "DeadLibraryAnalyzer",
    "DeadLibraryFinding",
    "DeadLibraryResolver",
    "FindingCategory",
    "LibraryUnit",
    "Recommendation",
    "Reference",
    "ReferenceKind",
    "SizeAnalysis",
    "SizeSummary",
    "UsageRecord",
    "aggregate_library_units",
    "assess_usage",
    "classify_confidence",
    "compute_savings",
    "resolve_usage",
    "summarize_sizes",
]
