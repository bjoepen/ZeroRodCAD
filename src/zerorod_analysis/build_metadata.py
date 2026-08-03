"""Single source of truth for current Build 020 release metadata."""

BUILD_ID = "020-M4"
SCANNER_NAME = "ZeroRodCAD Scanner 2.0"
BENCHMARK_NAME = "ZeroRodCAD Analysis Benchmark"


def scanner_version() -> str:
    return f"{SCANNER_NAME} – Build {BUILD_ID}"


def benchmark_version() -> str:
    return f"{BENCHMARK_NAME} – Build {BUILD_ID}"
