#!/usr/bin/env python3
"""Read-only macOS runtime trace controller."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))

from zerorod_analysis.build_metadata import BUILD_ID, runtime_trace_version  # noqa: E402
from zerorod_analysis.runtime.merge import merge_evidence  # noqa: E402
from zerorod_analysis.runtime.models import (  # noqa: E402
    EvidenceKind,
    EvidenceStatus,
    RuntimeTrace,
    TraceEvidence,
)
from zerorod_analysis.runtime.normalize import normalize_path  # noqa: E402
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

_DYLD_LINE = re.compile(r"(?:dyld(?:\[\d+\])?:\s*)?loaded:\s*(/\S+)", re.IGNORECASE)
_QT_LOADED = re.compile(
    r"(?:successfully\s+loaded\s+library|loaded\s+library)\s+['\"]?([^'\"\s]+)",
    re.IGNORECASE,
)
_NATIVE_SUFFIXES = tuple(__import__("importlib").machinery.EXTENSION_SUFFIXES)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _evidence_for_path(path: str, kind: EvidenceKind, source: str, bundle: Path) -> TraceEvidence:
    normalized = normalize_path(path, bundle_root=bundle)
    return TraceEvidence(
        identity=normalized.identity,
        kind=kind,
        status=normalized.status,
        sources=(source,),
        bundle_relative_path=normalized.bundle_relative_path,
    )


def parse_dyld_output(text: str, bundle_root: Path) -> tuple[TraceEvidence, ...]:
    evidence: list[TraceEvidence] = []
    for line in text.splitlines():
        match = _DYLD_LINE.search(line)
        if not match:
            continue
        path = match.group(1).rstrip(".,")
        kind = EvidenceKind.FRAMEWORK if ".framework/" in path else EvidenceKind.DYLIB
        evidence.append(_evidence_for_path(path, kind, "dyld", bundle_root))
    return merge_evidence(evidence)


def parse_qt_output(text: str, bundle_root: Path) -> tuple[TraceEvidence, ...]:
    evidence: list[TraceEvidence] = []
    for line in text.splitlines():
        match = _QT_LOADED.search(line)
        if match and Path(match.group(1)).is_absolute():
            evidence.append(
                _evidence_for_path(match.group(1), EvidenceKind.QT_PLUGIN, "qt-debug", bundle_root)
            )
    return merge_evidence(evidence)


def _read_raw(
    path: Path, bundle: Path
) -> tuple[list[TraceEvidence], Counter[str], bool, list[str]]:
    evidence: list[TraceEvidence] = []
    counts: Counter[str] = Counter()
    ended = False
    errors: list[str] = []
    if not path.is_file():
        return evidence, counts, False, ["runtime hook produced no raw trace"]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for number, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"invalid raw record at line {number}")
            continue
        event = str(record.get("event", "unknown"))
        counts[event] += 1
        if event == "end":
            ended = True
            errors.extend(str(item) for item in record.get("errors", ()))
        elif event == "recorder-error":
            errors.append(str(record.get("message", "unknown recorder error")))
        elif event in {"audit-import", "module-snapshot"}:
            name = str(record.get("name", ""))
            if not name:
                continue
            raw_module_path = record.get("path")
            loader = str(record.get("loader", ""))
            is_extension = loader == "ExtensionFileLoader" or (
                raw_module_path and str(raw_module_path).endswith(_NATIVE_SUFFIXES)
            )
            kind = EvidenceKind.NATIVE_EXTENSION if is_extension else EvidenceKind.PYTHON_MODULE
            normalized = (
                normalize_path(str(raw_module_path), bundle_root=bundle)
                if raw_module_path
                else None
            )
            source = "audit" if event == "audit-import" else f"sys.modules:{record.get('phase')}"
            evidence.append(
                TraceEvidence(
                    identity=name,
                    kind=kind,
                    status=EvidenceStatus.OBSERVED,
                    sources=(source,),
                    bundle_relative_path=normalized.bundle_relative_path if normalized else None,
                    details=(normalized.identity,) if normalized else (),
                )
            )
        elif event == "audit-native-load":
            value = str(record.get("value", ""))
            if value:
                evidence.append(
                    _evidence_for_path(value, EvidenceKind.DYLIB, "python-audit", bundle)
                )
    return evidence, counts, ended, errors


def _bundle_executable(bundle: Path) -> Path:
    if bundle.suffix != ".app" or not bundle.is_dir():
        raise ValueError("APP_BUNDLE must be an existing .app directory")
    macos = bundle / "Contents" / "MacOS"
    plist = bundle / "Contents" / "Info.plist"
    candidate: Path | None = None
    if plist.is_file():
        with plist.open("rb") as stream:
            name = plistlib.load(stream).get("CFBundleExecutable")
        if name:
            candidate = macos / str(name)
    if candidate is None:
        candidates = sorted(
            path for path in macos.iterdir() if path.is_file() and os.access(path, os.X_OK)
        )
        if len(candidates) == 1:
            candidate = candidates[0]
    if candidate is None or not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise ValueError("app bundle has no unambiguous executable")
    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect read-only runtime evidence from a macOS app"
    )
    parser.add_argument("app_bundle", type=Path, nargs="?")
    parser.add_argument("--profile", choices=TRACE_PROFILES, default=TRACE_PROFILES[0])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--no-dyld", action="store_true")
    parser.add_argument("--no-qt-debug", action="store_true")
    parser.add_argument("--version", action="version", version=runtime_trace_version())
    return parser


def _terminate(process: subprocess.Popen[str], grace: float = 3.0) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def collect_trace(args: argparse.Namespace) -> tuple[RuntimeTrace, Path | None]:
    if args.app_bundle is None or args.output is None:
        raise ValueError("APP_BUNDLE and --output are required")
    if args.timeout <= 0:
        raise ValueError("--timeout must be positive")
    bundle = args.app_bundle.expanduser().resolve(strict=False)
    executable = _bundle_executable(bundle)
    output = validate_output_path(args.output, bundle)
    started = _utc_now()
    timed_out = False
    exit_code: int | None = None
    stdout = ""
    stderr = ""
    with tempfile.TemporaryDirectory(prefix="zerorod-runtime-trace-") as temporary_name:
        temporary = Path(temporary_name)
        raw_path = temporary / "hook.jsonl"
        stimulus = temporary / "stimulus"
        isolated_home = temporary / "home"
        stimulus.mkdir()
        isolated_home.mkdir()
        environment = os.environ.copy()
        environment.update(
            {
                TRACE_ENABLE_ENV: "1",
                TRACE_RAW_PATH_ENV: str(raw_path),
                TRACE_BUNDLE_ROOT_ENV: str(bundle),
                TRACE_PROFILE_ENV: args.profile,
                TRACE_STIMULUS_DIR_ENV: str(stimulus),
                "HOME": str(isolated_home),
                "QT_QPA_PLATFORM": "offscreen",
            }
        )
        if not args.no_dyld:
            environment["DYLD_PRINT_LIBRARIES"] = "1"
        if not args.no_qt_debug:
            environment["QT_DEBUG_PLUGINS"] = "1"
        process = subprocess.Popen(
            [str(executable), "--startup-test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=args.timeout)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate(process)
            stdout, stderr = process.communicate()
            exit_code = process.returncode
        hook_evidence, counts, ended, errors = _read_raw(raw_path, bundle)
        dyld = () if args.no_dyld else parse_dyld_output(stderr, bundle)
        qt = () if args.no_qt_debug else parse_qt_output(stderr, bundle)
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
        kept: Path | None = None
        if args.keep_raw:
            kept = output.parent / f"{output.stem}-raw"
            kept.mkdir(parents=True, exist_ok=True)
            if raw_path.exists():
                shutil.copy2(raw_path, kept / raw_path.name)
            (kept / "stdout.txt").write_text(stdout, encoding="utf-8")
            (kept / "stderr.txt").write_text(stderr, encoding="utf-8")
        write_trace_atomic(trace, output, bundle_root=bundle)
    return trace, kept


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        trace, kept = collect_trace(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Runtime trace failed: {exc}", file=sys.stderr)
        return 2
    print(f"Runtime trace written to: {args.output}")
    if kept:
        print(f"Raw diagnostics kept at: {kept}")
    return 0 if trace.exit_status == "exited" and not trace.incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())
