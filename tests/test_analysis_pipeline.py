from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from zerorod_analysis import analyze_bundle
from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.exceptions import StageExecutionError
from zerorod_analysis.pipeline import AnalysisPipeline, PipelineContext
from zerorod_analysis.pipeline.stages import MachOStage, ScannerStage
from zerorod_analysis.scanner import Scanner


def make_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "Fixture.app"
    executable = bundle / "Contents" / "MacOS" / "fixture"
    executable.parent.mkdir(parents=True)
    executable.write_text("not a Mach-O file", encoding="utf-8")
    return bundle


def test_default_stage_order() -> None:
    assert AnalysisPipeline.default().stage_names == (
        "scanner",
        "macho",
        "dead-libraries",
        "advisor",
    )


def test_analyze_bundle_delegates_to_pipeline(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    from zerorod_analysis import api

    expected = DeadLibraryAnalysisResult()
    observed: list[PipelineContext] = []

    class RecordingPipeline:
        def run(self, context: PipelineContext) -> DeadLibraryAnalysisResult:
            observed.append(context)
            return expected

    monkeypatch.setattr(api.AnalysisPipeline, "default", lambda: RecordingPipeline())

    result = api.analyze_bundle(
        "Fixture.app",
        cache_dir=tmp_path / "cache",
        use_cache=False,
    )

    assert result is expected
    assert len(observed) == 1
    assert observed[0].bundle_path == Path("Fixture.app")
    assert observed[0].use_cache is False


def test_each_stage_runs_once_with_shared_context() -> None:
    calls: list[tuple[str, int]] = []
    result = DeadLibraryAnalysisResult()

    @dataclass
    class RecordingStage:
        name: str

        def run(self, context: PipelineContext) -> None:
            calls.append((self.name, id(context)))
            if self.name == "last":
                context.dead_library_result = result

    context = PipelineContext(Path("Fixture.app"))
    pipeline = AnalysisPipeline((RecordingStage("first"), RecordingStage("last")))

    assert pipeline.run(context) is result
    assert calls == [("first", id(context)), ("last", id(context))]


def test_pipeline_wraps_stage_failure_with_diagnostics() -> None:
    class BrokenStage:
        name = "broken"

        def run(self, context: PipelineContext) -> None:
            raise ValueError("original cause")

    bundle = Path("Broken.app")
    with pytest.raises(StageExecutionError) as error:
        AnalysisPipeline((BrokenStage(),)).run(PipelineContext(bundle))

    assert error.value.stage_name == "broken"
    assert error.value.bundle_path == bundle
    assert isinstance(error.value.__cause__, ValueError)
    assert "original cause" in str(error.value)


def test_minimal_bundle_runs_complete_pipeline_without_cache(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)

    result = analyze_bundle(bundle, cache_dir=tmp_path / "cache", use_cache=False)

    assert isinstance(result, DeadLibraryAnalysisResult)
    assert result.bundle_root == bundle.resolve()
    assert not (tmp_path / "cache").exists()


def test_scanner_stage_forwards_no_cache_configuration(tmp_path: Path) -> None:
    calls: list[tuple[Path | None, bool]] = []

    class RecordingScanner(Scanner):
        def scan(self, app_bundle: Path, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((kwargs["cache_dir"], kwargs["use_cache"]))
            return super().scan(app_bundle, **kwargs)

    context = PipelineContext(
        make_bundle(tmp_path),
        cache_dir=tmp_path / "disabled-cache",
        use_cache=False,
    )
    ScannerStage(scanner=RecordingScanner()).run(context)

    assert calls == [(tmp_path / "disabled-cache", False)]
    assert not (tmp_path / "disabled-cache").exists()


def test_macho_stage_builds_dependency_graph_once(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    from zerorod_analysis.pipeline.stages import macho as stage_module

    context = PipelineContext(make_bundle(tmp_path), use_cache=False)
    ScannerStage().run(context)
    original = stage_module.build_dependency_graph
    calls = 0

    def counting_builder(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(stage_module, "build_dependency_graph", counting_builder)
    MachOStage().run(context)

    assert calls == 1
    assert context.dependency_graph is not None
