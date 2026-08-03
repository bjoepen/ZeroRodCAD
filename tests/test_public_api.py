from zerorod_analysis import (
    analyze_bundle,
    calculate_bundle_health,
    generate_action_plan,
    generate_reports,
)
from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult


def test_public_api_functions_are_callable() -> None:
    assert all(
        callable(item)
        for item in (
            analyze_bundle,
            generate_reports,
            generate_action_plan,
            calculate_bundle_health,
        )
    )


def test_action_plan_and_health_delegate_to_existing_logic() -> None:
    analysis = DeadLibraryAnalysisResult()
    assert "Optimization Plan" in generate_action_plan(analysis)
    assert calculate_bundle_health(analysis).score == 100
