from pathlib import Path

import pytest

from zerorod_analysis.exceptions import MissingStageResultError
from zerorod_analysis.pipeline import AnalysisStage, PipelineContext
from zerorod_analysis.pipeline.stages import (
    AdvisorStage,
    DeadLibraryStage,
    MachOStage,
    ScannerStage,
)


@pytest.mark.parametrize(
    "stage",
    [ScannerStage(), MachOStage(), DeadLibraryStage(), AdvisorStage()],
)
def test_default_stages_implement_typed_contract(stage: object) -> None:
    assert isinstance(stage, AnalysisStage)


@pytest.mark.parametrize(
    ("stage", "missing_result"),
    [
        (MachOStage(), "database"),
        (DeadLibraryStage(), "database"),
        (AdvisorStage(), "dead_library_result"),
    ],
)
def test_stage_requires_its_predecessor(stage: AnalysisStage, missing_result: str) -> None:
    context = PipelineContext(Path("Missing.app"))

    with pytest.raises(MissingStageResultError) as error:
        stage.run(context)

    assert error.value.stage_name == stage.name
    assert error.value.result_name == missing_result
    assert "Missing.app" in str(error.value)
