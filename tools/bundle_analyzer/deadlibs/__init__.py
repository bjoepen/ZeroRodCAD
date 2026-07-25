"""Public API for Build 019.3 dead-library analysis."""

from .advisor import (
    Advice,
    BundleHealth,
    BundleHealthEvaluator,
    RecommendationAdvisor,
    RiskEvaluator,
)
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
from .report import (
    bundle_size_markdown,
    dead_libraries_markdown,
    optimization_markdown,
    optimization_plan_markdown,
    result_payload,
    write_dead_library_reports,
)
from .resolver import DeadLibraryResolver, resolve_usage
from .size import SizeAnalysis, SizeSummary, compute_savings, summarize_sizes

__all__ = [
    "Advice",
    "BundleHealth",
    "BundleHealthEvaluator",
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
    "RecommendationAdvisor",
    "RiskEvaluator",
    "SizeAnalysis",
    "SizeSummary",
    "UsageRecord",
    "aggregate_library_units",
    "bundle_size_markdown",
    "dead_libraries_markdown",
    "assess_usage",
    "classify_confidence",
    "compute_savings",
    "optimization_markdown",
    "optimization_plan_markdown",
    "result_payload",
    "resolve_usage",
    "summarize_sizes",
    "write_dead_library_reports",
]
