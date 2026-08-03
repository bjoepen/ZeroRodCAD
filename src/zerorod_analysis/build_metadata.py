"""Single source of truth for current analyzer release metadata."""

BUILD_ID = "021-M1"
SCANNER_NAME = "ZeroRodCAD Scanner 2.0"
BENCHMARK_NAME = "ZeroRodCAD Analysis Benchmark"
RUNTIME_TRACE_NAME = "ZeroRodCAD Runtime Trace"


def scanner_version() -> str:
    return f"{SCANNER_NAME} – Build {BUILD_ID}"


def benchmark_version() -> str:
    return f"{BENCHMARK_NAME} – Build {BUILD_ID}"


def runtime_trace_version() -> str:
    return f"{RUNTIME_TRACE_NAME} – Build {BUILD_ID}"
