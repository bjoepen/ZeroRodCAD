"""Dead-library analysis foundation for ZeroRodCAD bundle inspection."""

from .confidence import classify_confidence
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
from .resolver import DeadLibraryResolver
from .size import SizeSummary, summarize_sizes

__all__ = [
    "ConfidenceLevel",
    "DeadLibraryAnalysisResult",
    "DeadLibraryFinding",
    "DeadLibraryResolver",
    "FindingCategory",
    "LibraryUnit",
    "Recommendation",
    "Reference",
    "ReferenceKind",
    "SizeSummary",
    "UsageRecord",
    "classify_confidence",
    "summarize_sizes",
]
