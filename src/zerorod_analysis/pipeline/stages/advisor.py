"""Advisor stage."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...advisor import BundleHealthEvaluator, RecommendationAdvisor
from ...exceptions import MissingStageResultError
from ..context import PipelineContext


@dataclass(slots=True)
class AdvisorStage:
    """Evaluate existing findings without repeating earlier analysis."""

    name: str = "advisor"
    advisor: RecommendationAdvisor = field(default_factory=RecommendationAdvisor)
    health_evaluator: BundleHealthEvaluator = field(default_factory=BundleHealthEvaluator)

    def run(self, context: PipelineContext) -> None:
        if context.dead_library_result is None:
            raise MissingStageResultError(self.name, context.bundle_path, "dead_library_result")
        context.advisor_results = tuple(
            self.advisor.advise(finding) for finding in context.dead_library_result.findings
        )
        context.bundle_health = self.health_evaluator.evaluate(context.dead_library_result)
