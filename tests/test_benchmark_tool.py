import json
import subprocess
import sys
from pathlib import Path

from zerorod_analysis.benchmark import benchmark_bundle
from zerorod_analysis.build_metadata import benchmark_version


def make_bundle(tmp_path: Path) -> Path:
    executable = tmp_path / "Benchmark.app" / "Contents" / "MacOS" / "benchmark"
    executable.parent.mkdir(parents=True)
    executable.write_text("not Mach-O", encoding="utf-8")
    return executable.parents[2]


def test_benchmark_honors_warmup_iterations_and_no_cache(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    from zerorod_analysis import benchmark as module

    calls: list[bool] = []
    report_directories: list[Path] = []
    real_analyze = module.analyze_bundle
    real_generate = module.ReportEngine.generate_with_metrics

    def recording_analyze(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs["use_cache"])
        return real_analyze(*args, **kwargs)

    def recording_generate(self, result, request):  # type: ignore[no-untyped-def]
        report_directories.append(request.output_directory)
        return real_generate(self, result, request)

    monkeypatch.setattr(module, "analyze_bundle", recording_analyze)
    monkeypatch.setattr(module.ReportEngine, "generate_with_metrics", recording_generate)

    result = benchmark_bundle(make_bundle(tmp_path), iterations=2, warmup=1, use_cache=False)

    assert result.iterations == 2
    assert result.warmup == 1
    assert calls == [False, False, False]
    assert len(report_directories) == 3
    assert all(not path.exists() for path in report_directories)


def test_benchmark_cli_writes_valid_json(tmp_path: Path) -> None:
    repository_root = Path(__file__).parents[1]
    output = tmp_path / "benchmark.json"
    process = subprocess.run(
        [
            sys.executable,
            "tools/benchmark_analysis.py",
            str(make_bundle(tmp_path)),
            "--warmup",
            "0",
            "--iterations",
            "2",
            "--no-cache",
            "--json-output",
            str(output),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 0, process.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["iterations"] == 2
    assert payload["schema"] == "zerorod-analysis/benchmark/v1"


def test_benchmark_cli_reports_invalid_bundle(tmp_path: Path) -> None:
    repository_root = Path(__file__).parents[1]
    process = subprocess.run(
        [sys.executable, "tools/benchmark_analysis.py", str(tmp_path / "Missing.app")],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode != 0
    assert "Benchmark fehlgeschlagen" in process.stderr


def test_benchmark_version_is_centralized() -> None:
    assert "021-M1" in benchmark_version()
