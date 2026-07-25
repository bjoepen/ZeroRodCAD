"""Explainable optimization advice for dead-library findings."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ConfidenceLevel,
    DeadLibraryAnalysisResult,
    DeadLibraryFinding,
    FindingCategory,
    Recommendation,
    ReferenceKind,
)


@dataclass(frozen=True, slots=True)
class Advice:
    """Explainable recommendation metadata for one finding."""

    recommendation: Recommendation
    risk_score: int
    risk_label: str
    reasons: tuple[str, ...]
    actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BundleHealth:
    """Aggregate optimization health score for a bundle."""

    score: int
    grade: str
    deductions: tuple[str, ...]


class RiskEvaluator:
    """Calculate a conservative removal-risk score in the range 0..100."""

    _confidence_penalty = {
        ConfidenceLevel.HIGH: 0,
        ConfidenceLevel.MEDIUM: 18,
        ConfidenceLevel.LOW: 35,
    }

    def evaluate(self, finding: DeadLibraryFinding) -> int:
        score = self._confidence_penalty[finding.confidence]
        kinds = {reference.kind for reference in finding.usage.references}

        if finding.recommendation is Recommendation.KEEP:
            score += 45
        elif finding.recommendation is Recommendation.REVIEW:
            score += 20

        if ReferenceKind.MACHO_DEPENDENCY in kinds or ReferenceKind.MACHO in kinds:
            score += 35
        if ReferenceKind.PYTHON_IMPORT in kinds:
            score += 30
        if ReferenceKind.PLUGIN_MANIFEST in kinds:
            score += 30
        if kinds & {ReferenceKind.DYNAMIC_LOAD, ReferenceKind.DYNAMIC_LOAD_HINT}:
            score += 30
        if finding.usage.unresolved_hints:
            score += 20
        if finding.library.category is FindingCategory.PYTHON_PACKAGE:
            score += 10
        if finding.library.category is FindingCategory.RESOURCE:
            score += 15
        if finding.library.category is FindingCategory.DUPLICATE:
            score -= 15

        return max(0, min(100, score))

    @staticmethod
    def label(score: int) -> str:
        if not 0 <= score <= 100:
            raise ValueError("risk score must be between 0 and 100")
        if score <= 20:
            return "very-low"
        if score <= 40:
            return "low"
        if score <= 65:
            return "medium"
        if score <= 85:
            return "high"
        return "critical"


class RecommendationAdvisor:
    """Convert analysis evidence into explainable, actionable advice."""

    def __init__(self, evaluator: RiskEvaluator | None = None) -> None:
        self.evaluator = evaluator or RiskEvaluator()

    def advise(self, finding: DeadLibraryFinding) -> Advice:
        risk_score = self.evaluator.evaluate(finding)
        reasons = list(finding.reasons)
        kinds = {reference.kind for reference in finding.usage.references}

        evidence_labels = {
            ReferenceKind.MACHO: "Mach-O usage evidence exists.",
            ReferenceKind.MACHO_DEPENDENCY: "A Mach-O dependency resolves to this library.",
            ReferenceKind.PYTHON_IMPORT: "A Python import references this library.",
            ReferenceKind.PLUGIN_MANIFEST: "A plug-in manifest references this library.",
            ReferenceKind.DYNAMIC_LOAD: "Runtime loading evidence references this library.",
            ReferenceKind.DYNAMIC_LOAD_HINT: "A dynamic-loading hint references this library.",
        }
        reasons.extend(
            label
            for kind, label in evidence_labels.items()
            if kind in kinds and label not in reasons
        )
        if finding.usage.unresolved_hints:
            reasons.append("Unresolved loading hints require manual verification.")

        actions = self._actions(finding.recommendation)
        return Advice(
            recommendation=finding.recommendation,
            risk_score=risk_score,
            risk_label=self.evaluator.label(risk_score),
            reasons=tuple(dict.fromkeys(reasons)),
            actions=actions,
        )

    @staticmethod
    def _actions(recommendation: Recommendation) -> tuple[str, ...]:
        if recommendation is Recommendation.SAFE_REMOVE:
            return (
                "Create a copy of the application bundle.",
                "Remove only this candidate from the copy.",
                "Launch the application and test affected workflows.",
                "Rebuild the bundle if validation succeeds.",
            )
        if recommendation is Recommendation.REVIEW:
            return (
                "Collect runtime-import or loader traces.",
                "Inspect plug-in and configuration manifests.",
                "Keep the library until usage is disproved.",
            )
        return ("Keep the library in the bundle.",)


class BundleHealthEvaluator:
    """Calculate a stable high-level bundle health indicator."""

    def evaluate(self, result: DeadLibraryAnalysisResult) -> BundleHealth:
        if not result.findings:
            return BundleHealth(score=100, grade="excellent", deductions=())

        advisor = RecommendationAdvisor()
        advices = [advisor.advise(finding) for finding in result.findings]
        count = len(result.findings)
        safe_count = sum(
            finding.recommendation is Recommendation.SAFE_REMOVE for finding in result.findings
        )
        review_count = sum(
            finding.recommendation is Recommendation.REVIEW for finding in result.findings
        )
        duplicate_count = sum(
            finding.library.category is FindingCategory.DUPLICATE for finding in result.findings
        )
        dynamic_count = sum(
            bool(finding.usage.dynamic_hints or finding.usage.unresolved_hints)
            for finding in result.findings
        )
        average_risk = sum(advice.risk_score for advice in advices) / count

        bundle_size = max(result.total_bundle_size_bytes, 1)
        savings_ratio = min(1.0, result.potential_savings_bytes / bundle_size)
        deduction_values = {
            "unused libraries": min(25, round(25 * safe_count / count)),
            "review candidates": min(20, round(20 * review_count / count)),
            "duplicates": min(15, round(15 * duplicate_count / count)),
            "dynamic or unresolved loads": min(20, round(20 * dynamic_count / count)),
            "aggregate removal risk": min(15, round(15 * average_risk / 100)),
            "potential bundle waste": min(15, round(15 * savings_ratio)),
        }
        deductions = tuple(
            f"-{value}: {label}" for label, value in deduction_values.items() if value
        )
        score = max(0, 100 - sum(deduction_values.values()))
        return BundleHealth(score=score, grade=self._grade(score), deductions=deductions)

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "excellent"
        if score >= 75:
            return "good"
        if score >= 60:
            return "fair"
        if score >= 40:
            return "poor"
        return "critical"
