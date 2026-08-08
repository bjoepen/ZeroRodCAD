"""TE-002.1 reproducible sidecar runtime/deployment benchmark (section 38).

Compares one-shot (onefile/onedir) and persistent sidecar runs. No new
dependencies: RSS via the `ps` system tool, percentiles via stdlib
`statistics`. Outputs machine-readable JSON plus a human-readable summary.

Usage:
    python tools/poc/tauri/benchmark_sidecar_runtime.py oneshot \
        --binary experiments/te002-tauri/src-tauri/binaries/zerorod-engine-aarch64-apple-darwin \
        --label onefile --runs 20 --output build/reports/te0021/variant-a.json

    python tools/poc/tauri/benchmark_sidecar_runtime.py persistent \
        --binary dist-onedir/zerorod-engine/zerorod-engine \
        --requests 20 --output build/reports/te0021/variant-c.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

SIDECAR_SCHEMA = "zerorod-sidecar/v1"


def _preview_request(request_id: str) -> str:
    return (
        json.dumps(
            {
                "schema": SIDECAR_SCHEMA,
                "request_id": request_id,
                "command": "preview",
                "parameters": {},
            }
        )
        + "\n"
    )


def _shutdown_request(request_id: str) -> str:
    return (
        json.dumps({"schema": SIDECAR_SCHEMA, "request_id": request_id, "command": "shutdown"})
        + "\n"
    )


def _rss_kb_single(pid: int) -> int | None:
    try:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=5
        )
        text = result.stdout.strip()
        return int(text) if text else None
    except Exception:
        return None


def _child_pids(pid: int) -> list[int]:
    try:
        result = subprocess.run(
            ["pgrep", "-P", str(pid)], capture_output=True, text=True, timeout=5
        )
        return [int(p) for p in result.stdout.split()]
    except Exception:
        return []


def _rss_kb(pid: int) -> int | None:
    """Real, measured RSS via the macOS/BSD `ps` tool — no new dependency.

    IMPORTANT (found empirically during Variant C benchmarking): a
    PyInstaller **onefile** executable's own process is a lightweight
    bootloader that self-extracts and then forks/execs a *child* process
    which does all the real work (imports cadquery/OCP, builds the model,
    etc.) — the bootloader's own RSS stays ~1.5 MB for the process's entire
    life, while the real worker child measured ~320 MB. Measuring only the
    top-level PID silently reports the bootloader's near-empty footprint,
    not the actual memory in use. onedir builds do NOT fork (verified: 0
    children, RSS matches the onefile *worker* child almost exactly), so
    this walk is a no-op for them. Always resolves to the deepest live
    descendant to get a real number for both packaging modes.
    """
    current = pid
    for _ in range(5):  # bounded walk — a real process tree is never this deep here
        children = _child_pids(current)
        if not children:
            break
        current = children[0]
    return _rss_kb_single(current)


def _dist(values: list[float]) -> dict:
    if not values:
        return {"min": None, "median": None, "p95": None, "max": None}
    ordered = sorted(values)
    if len(ordered) >= 2:
        p95 = statistics.quantiles(ordered, n=100, method="inclusive")[94]
    else:
        p95 = ordered[0]
    return {
        "min": ordered[0],
        "median": statistics.median(ordered),
        "p95": p95,
        "max": ordered[-1],
    }


def _dir_size_and_count(path: Path) -> tuple[int, int]:
    if path.is_file():
        return path.stat().st_size, 1
    total_bytes = 0
    file_count = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total_bytes += entry.stat().st_size
            file_count += 1
    return total_bytes, file_count


def bench_oneshot(binary: Path, label: str, runs: int) -> dict:
    durations: list[float] = []
    payload_bytes: int | None = None
    engine_timing: dict | None = None
    failures: list[str] = []

    for i in range(runs):
        request = _preview_request(f"bench-{label}-{i}")
        started = time.perf_counter()
        try:
            result = subprocess.run(
                [str(binary)], input=request, capture_output=True, text=True, timeout=90
            )
        except subprocess.TimeoutExpired:
            failures.append(f"run {i}: timed out")
            continue
        elapsed = time.perf_counter() - started
        durations.append(elapsed)
        if result.returncode != 0:
            failures.append(f"run {i}: exit code {result.returncode}: {result.stderr[-500:]}")
            continue
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            failures.append(f"run {i}: expected 1 stdout line, got {len(lines)}")
            continue
        response = json.loads(lines[0])
        if not response.get("ok"):
            failures.append(f"run {i}: sidecar reported error: {response.get('error')}")
            continue
        if payload_bytes is None:
            payload_bytes = len(result.stdout.encode("utf-8"))
            engine_timing = response["result"].get("timing")

    disk_bytes, file_count = _dir_size_and_count(binary.parent if binary.is_file() else binary)

    return {
        "mode": "oneshot",
        "label": label,
        "binary": str(binary),
        "runs_requested": runs,
        "runs_succeeded": len(durations),
        "failures": failures,
        "roundtrip_seconds": _dist(durations),
        "raw_durations_seconds": durations,
        "payload_bytes": payload_bytes,
        "engine_timing": engine_timing,
        "deployment_disk_bytes": disk_bytes,
        "deployment_file_count": file_count,
    }


def measure_rss_snapshot(binary: Path) -> dict:
    """Launches the binary, holds stdin open (blocking its readline()) so a
    live RSS snapshot can be taken before any request is processed, then
    completes the request normally. Mirrors the technique used in TE-002's
    own OS-level check.
    """
    import os

    read_fd, write_fd = os.pipe()
    process = subprocess.Popen(
        [str(binary)],
        stdin=read_fd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        close_fds=False,
    )
    os.close(read_fd)
    time.sleep(0.3)  # let the process finish loading its interpreter/imports
    rss_kb = _rss_kb(process.pid)
    os.write(write_fd, _preview_request("rss-snapshot").encode("utf-8"))
    os.close(write_fd)
    try:
        stdout, stderr = process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
    return {"rss_kb_before_request": rss_kb, "exit_code": process.returncode}


def bench_persistent(binary: Path, requests: int) -> dict:
    process = subprocess.Popen(
        [str(binary), "--persistent"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    cold_start = time.perf_counter()
    process.stdin.write(_preview_request("bench-persistent-cold"))
    process.stdin.flush()
    first_line = process.stdout.readline()
    cold_duration = time.perf_counter() - cold_start
    first_response = json.loads(first_line)
    payload_bytes = len(first_line.encode("utf-8"))
    engine_timing = first_response["result"].get("timing") if first_response.get("ok") else None

    rss_by_checkpoint: dict[str, int | None] = {"after_request_1": _rss_kb(process.pid)}

    warm_durations: list[float] = []
    for i in range(2, requests + 1):
        started = time.perf_counter()
        process.stdin.write(_preview_request(f"bench-persistent-warm-{i}"))
        process.stdin.flush()
        line = process.stdout.readline()
        warm_durations.append(time.perf_counter() - started)
        json.loads(line)  # validate each response is well-formed JSON
        if i in (5, 10, 20):
            rss_by_checkpoint[f"after_request_{i}"] = _rss_kb(process.pid)

    process.stdin.write(_shutdown_request("bench-persistent-shutdown"))
    process.stdin.flush()
    shutdown_line = process.stdout.readline()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    disk_bytes, file_count = _dir_size_and_count(binary.parent if binary.is_file() else binary)

    return {
        "mode": "persistent",
        "binary": str(binary),
        "requests_requested": requests,
        "cold_start_seconds": cold_duration,
        "warm_roundtrip_seconds": _dist(warm_durations),
        "raw_warm_durations_seconds": warm_durations,
        "payload_bytes": payload_bytes,
        "engine_timing_first_request": engine_timing,
        "rss_kb_by_checkpoint": rss_by_checkpoint,
        "shutdown_response_ok": json.loads(shutdown_line).get("ok")
        if shutdown_line.strip()
        else None,
        "process_exit_code": process.returncode,
        "deployment_disk_bytes": disk_bytes,
        "deployment_file_count": file_count,
    }


def _print_summary(result: dict) -> None:
    print(f"mode: {result['mode']}", file=sys.stderr)
    if result["mode"] == "oneshot":
        rt = result["roundtrip_seconds"]
        print(
            f"  roundtrip (s): min={rt['min']:.3f} median={rt['median']:.3f} "
            f"p95={rt['p95']:.3f} max={rt['max']:.3f}",
            file=sys.stderr,
        )
        print(
            f"  succeeded: {result['runs_succeeded']}/{result['runs_requested']}", file=sys.stderr
        )
        if result["failures"]:
            print(f"  failures: {result['failures']}", file=sys.stderr)
    else:
        wr = result["warm_roundtrip_seconds"]
        print(f"  cold start (s): {result['cold_start_seconds']:.3f}", file=sys.stderr)
        print(
            f"  warm roundtrip (s): min={wr['min']:.4f} median={wr['median']:.4f} "
            f"p95={wr['p95']:.4f} max={wr['max']:.4f}",
            file=sys.stderr,
        )
        print(f"  RSS by checkpoint (KB): {result['rss_kb_by_checkpoint']}", file=sys.stderr)
    print(
        f"  deployment: {result['deployment_disk_bytes']} bytes, "
        f"{result['deployment_file_count']} files",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TE-002.1 sidecar runtime benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    oneshot_parser = subparsers.add_parser("oneshot")
    oneshot_parser.add_argument("--binary", type=Path, required=True)
    oneshot_parser.add_argument("--label", required=True)
    oneshot_parser.add_argument("--runs", type=int, default=20)
    oneshot_parser.add_argument("--output", type=Path, required=True)
    oneshot_parser.add_argument("--rss-snapshot", action="store_true")

    persistent_parser = subparsers.add_parser("persistent")
    persistent_parser.add_argument("--binary", type=Path, required=True)
    persistent_parser.add_argument("--requests", type=int, default=20)
    persistent_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "oneshot":
        result = bench_oneshot(args.binary, args.label, args.runs)
        if args.rss_snapshot:
            result["rss_snapshot"] = measure_rss_snapshot(args.binary)
    else:
        result = bench_persistent(args.binary, args.requests)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Benchmark result written to: {args.output}", file=sys.stderr)
    _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
