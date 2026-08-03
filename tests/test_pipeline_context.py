from pathlib import Path

from zerorod_analysis.pipeline import PipelineContext


def test_context_normalizes_paths_without_running_analysis() -> None:
    context = PipelineContext(
        bundle_path="Example.app",
        cache_dir="cache",
        output_directory="reports",
        use_cache=False,
    )

    assert context.bundle_path == Path("Example.app")
    assert context.cache_dir == Path("cache")
    assert context.output_directory == Path("reports")
    assert context.use_cache is False
    assert context.database is None
    assert context.dependency_graph is None
    assert context.dead_library_result is None


def test_context_owns_independent_warning_lists() -> None:
    first = PipelineContext(Path("First.app"))
    second = PipelineContext(Path("Second.app"))

    first.warnings.append("first")

    assert second.warnings == []
