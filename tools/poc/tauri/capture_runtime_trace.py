#!/usr/bin/env python3
"""TE-002.2B — capture a runtime trace against the sidecar binary directly.

`tools/trace_runtime.py` requires a `.app` bundle with a
`Contents/MacOS/<CFBundleExecutable>` entry point, because it was written for
the TE-001.x PySide6 desktop app. The Tauri sidecar has no such bundle of its
own (it is a `resources`-copied directory, not a `.app`), and the Tauri Rust
binary has no `--startup-test` flag to relay into it. This script reuses the
exact same evidence-extraction functions `trace_runtime.py` already has
(`_read_raw`, `parse_dyld_output`, `merge_evidence`, `RuntimeTrace`,
`write_trace_atomic`) against the sidecar executable directly, driving it
through one real `zerorod-sidecar/v1` protocol round trip over stdin/stdout
before it exits and the runtime hook's stimulus (see
`packaging/macos/runtime_hook.py`) fires at exit. Not a new trace engine —
the same recorder/audit-hook/parsing pipeline, wired to a different process
entry point.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.trace_runtime import (  # noqa: E402
    _read_raw,
    _utc_now,
    parse_dyld_output,
    parse_qt_output,
)

from zerorod_analysis.build_metadata import BUILD_ID  # noqa: E402
from zerorod_analysis.runtime.merge import merge_evidence  # noqa: E402
from zerorod_analysis.runtime.models import EvidenceKind, RuntimeTrace  # noqa: E402
from zerorod_analysis.runtime.schema import (  # noqa: E402
    TRACE_BUNDLE_ROOT_ENV,
    TRACE_ENABLE_ENV,
    TRACE_PROFILE_ENV,
    TRACE_PROFILES,
    TRACE_RAW_PATH_ENV,
    TRACE_SCHEMA_ID,
    TRACE_STIMULUS_DIR_ENV,
)
from zerorod_analysis.runtime.serialization import (  # noqa: E402
    validate_output_path,
    write_trace_atomic,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sidecar_binary", type=Path)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--profile", choices=TRACE_PROFILES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stimulus-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--protocol-round-trip",
        action="store_true",
        help="drive one real preview+shutdown round trip over stdin/stdout "
        "before the process exits (in addition to the exit-time stimulus)",
    )
    return parser


def _drive_protocol(process: subprocess.Popen[str]) -> dict[str, object]:
    def send(command: str, request_id: str) -> dict[str, object]:
        line = json.dumps(
            {
                "schema": "zerorod-sidecar/v1",
                "request_id": request_id,
                "command": command,
                "parameters": {},
            }
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(line + "\n")
        process.stdin.flush()
        raw = process.stdout.readline()
        return json.loads(raw) if raw else {"ok": False, "error": "no response (EOF)"}

    preview = send("preview", "trace-preview-1")
    shutdown = send("shutdown", "trace-shutdown-1")
    return {"preview": preview, "shutdown": shutdown}


def capture(args: argparse.Namespace) -> tuple[RuntimeTrace, dict[str, object] | None]:
    bundle = args.bundle_root.expanduser().resolve(strict=False)
    output = validate_output_path(args.output, bundle)
    args.stimulus_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output.parent / f"{args.output.stem}-raw.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists():
        raw_path.unlink()

    environment = os.environ.copy()
    environment.update(
        {
            TRACE_ENABLE_ENV: "1",
            TRACE_RAW_PATH_ENV: str(raw_path),
            TRACE_BUNDLE_ROOT_ENV: str(bundle),
            TRACE_PROFILE_ENV: args.profile,
            TRACE_STIMULUS_DIR_ENV: str(args.stimulus_dir),
        }
    )

    started = _utc_now()
    protocol_result: dict[str, object] | None = None
    timed_out = False
    exit_code: int | None = None
    stderr = ""
    process = subprocess.Popen(
        [str(args.sidecar_binary), "--persistent"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=environment,
    )
    try:
        if args.protocol_round_trip:
            protocol_result = _drive_protocol(process)
        _, stderr = process.communicate(timeout=args.timeout)
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        _, stderr = process.communicate()
        exit_code = process.returncode

    hook_evidence, counts, ended, errors = _read_raw(raw_path, bundle)
    dyld = parse_dyld_output(stderr, bundle)
    qt = parse_qt_output(stderr, bundle)
    all_python = merge_evidence(
        item for item in hook_evidence if item.kind is EvidenceKind.PYTHON_MODULE
    )
    native = merge_evidence(
        item for item in hook_evidence if item.kind is EvidenceKind.NATIVE_EXTENSION
    )
    audit_libraries = [item for item in hook_evidence if item.kind is EvidenceKind.DYLIB]
    libraries = merge_evidence([*audit_libraries, *dyld])
    counts.update({"dyld-load": sum(item.event_count for item in dyld)})
    counts.update({"qt-plugin-load": sum(item.event_count for item in qt)})
    error = "; ".join(sorted(set(errors))) or None
    incomplete = timed_out or exit_code != 0 or not ended or error is not None
    trace = RuntimeTrace(
        schema=TRACE_SCHEMA_ID,
        build_id=BUILD_ID,
        python_version=sys.version.split()[0],
        platform=sys.platform,
        started_at=started,
        ended_at=_utc_now(),
        profile=args.profile,
        exit_status="timeout" if timed_out else ("exited" if exit_code == 0 else "failed"),
        exit_code=exit_code,
        timed_out=timed_out,
        incomplete=incomplete,
        python_modules=all_python,
        native_extensions=native,
        loaded_libraries=libraries,
        qt_plugins=qt,
        event_counts=tuple(sorted(counts.items())),
        error=error,
    )
    write_trace_atomic(trace, output, bundle_root=bundle)
    return trace, protocol_result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    trace, protocol_result = capture(args)
    print(f"Runtime trace written to: {args.output}")
    if protocol_result is not None:
        print(f"Protocol round trip: {json.dumps(protocol_result)[:300]}")
    print(
        f"profile={trace.profile} exit_status={trace.exit_status} "
        f"incomplete={trace.incomplete} python_modules={len(trace.python_modules)} "
        f"native_extensions={len(trace.native_extensions)}"
    )
    return 0 if trace.exit_status == "exited" and not trace.incomplete else 1


if __name__ == "__main__":
    t0 = time.time()
    rc = main()
    raise SystemExit(rc)
