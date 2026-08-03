"""Deterministic and safe runtime trace JSON serialization."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any

from .merge import evidence_sort_key
from .models import RuntimeTrace


def _json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def trace_json_bytes(trace: RuntimeTrace) -> bytes:
    trace = replace(
        trace,
        python_modules=tuple(sorted(trace.python_modules, key=evidence_sort_key)),
        native_extensions=tuple(sorted(trace.native_extensions, key=evidence_sort_key)),
        loaded_libraries=tuple(sorted(trace.loaded_libraries, key=evidence_sort_key)),
        qt_plugins=tuple(sorted(trace.qt_plugins, key=evidence_sort_key)),
        event_counts=tuple(sorted(trace.event_counts)),
    )
    content = json.dumps(
        _json_value(trace), ensure_ascii=False, indent=2, sort_keys=True, separators=(",", ": ")
    )
    return (content + "\n").encode("utf-8")


def validate_output_path(output: Path, bundle_root: Path | None = None) -> Path:
    if any(part == ".." for part in output.parts):
        raise ValueError("output path traversal is not allowed")
    resolved = output.expanduser().resolve(strict=False)
    if bundle_root is not None:
        bundle = bundle_root.expanduser().resolve(strict=False)
        try:
            resolved.relative_to(bundle)
        except ValueError:
            pass
        else:
            raise ValueError("output must be outside the analyzed app bundle")
    return resolved


def write_trace_atomic(
    trace: RuntimeTrace, output: Path, *, bundle_root: Path | None = None
) -> Path:
    target = validate_output_path(output, bundle_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(trace_json_bytes(trace))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target
