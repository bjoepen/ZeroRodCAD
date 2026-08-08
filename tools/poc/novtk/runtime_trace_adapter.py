"""TE-001 adapter over the Build 021 M1 runtime trace foundation.

Reuses the existing recorder (``packaging/macos/runtime_hook.py``), models,
parsers and serializer from ``zerorod_analysis.runtime`` / ``tools.trace_runtime``
verbatim. No parallel trace engine is implemented here — this module only wires
those pieces together for a plain-venv PoC process instead of a packaged
``.app`` bundle, which is the only thing ``tools/trace_runtime.py``'s bundle-
oriented CLI does not already support.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.trace_runtime import _read_raw, parse_dyld_output, parse_qt_output  # noqa: E402

from zerorod_analysis.build_metadata import BUILD_ID  # noqa: E402
from zerorod_analysis.runtime.merge import merge_evidence  # noqa: E402
from zerorod_analysis.runtime.models import EvidenceKind, RuntimeTrace  # noqa: E402
from zerorod_analysis.runtime.schema import (  # noqa: E402
    PROFILE_STARTUP_TEST,
    TRACE_ENABLE_ENV,
    TRACE_PROFILE_ENV,
    TRACE_RAW_PATH_ENV,
    TRACE_SCHEMA_ID,
)
from zerorod_analysis.runtime.serialization import write_trace_atomic  # noqa: E402

_RUNTIME_HOOK_PATH = REPO_ROOT / "packaging" / "macos" / "runtime_hook.py"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def enable_recording(raw_path: Path) -> None:
    """Install the Build 021 M1 recorder in the current process.

    Must be called before the first ``cadquery``/``OCP`` import so the audit
    hook and start snapshot cover the whole checkpoint sequence. Sets the same
    environment variables the recorder already understands, then loads
    ``runtime_hook.py`` (which self-activates when ``TRACE_ENABLE_ENV`` is set,
    exactly as it does inside a frozen PyInstaller bundle).
    """
    os.environ[TRACE_ENABLE_ENV] = "1"
    os.environ[TRACE_RAW_PATH_ENV] = str(raw_path)
    os.environ.setdefault(TRACE_PROFILE_ENV, PROFILE_STARTUP_TEST)
    spec = importlib.util.spec_from_file_location("te001_runtime_hook", _RUNTIME_HOOK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load runtime hook from {_RUNTIME_HOOK_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def build_trace(
    *,
    raw_path: Path,
    venv_root: Path,
    started_at: str,
    profile: str = PROFILE_STARTUP_TEST,
    exit_status: str,
    exit_code: int | None,
    timed_out: bool = False,
    dyld_stderr: str = "",
    qt_stderr: str = "",
) -> RuntimeTrace:
    """Build a ``RuntimeTrace`` from raw recorder output, reusing the M1 parsers.

    ``venv_root`` stands in for the bundle root the M1 controller normally
    scopes paths to: it lets cadquery/OCP/zerorodcad files installed inside
    ``.venv-novtk-poc`` normalize to short relative identities instead of
    SHA-256-redacted external paths, which would otherwise hide exactly which
    package produced each observation.
    """
    hook_evidence, counts, ended, errors = _read_raw(raw_path, venv_root)
    dyld = parse_dyld_output(dyld_stderr, venv_root) if dyld_stderr else ()
    qt = parse_qt_output(qt_stderr, venv_root) if qt_stderr else ()
    python_modules = merge_evidence(
        item for item in hook_evidence if item.kind is EvidenceKind.PYTHON_MODULE
    )
    native_extensions = merge_evidence(
        item for item in hook_evidence if item.kind is EvidenceKind.NATIVE_EXTENSION
    )
    audit_libraries = [item for item in hook_evidence if item.kind is EvidenceKind.DYLIB]
    loaded_libraries = merge_evidence([*audit_libraries, *dyld])
    counts.update({"dyld-load": sum(item.event_count for item in dyld)})
    counts.update({"qt-plugin-load": sum(item.event_count for item in qt)})
    error = "; ".join(sorted(set(errors))) or None
    incomplete = timed_out or exit_code not in (0, None) or not ended or error is not None
    return RuntimeTrace(
        schema=TRACE_SCHEMA_ID,
        build_id=BUILD_ID,
        python_version=sys.version.split()[0],
        platform=sys.platform,
        started_at=started_at,
        ended_at=_utc_now(),
        profile=profile,
        exit_status=exit_status,
        exit_code=exit_code,
        timed_out=timed_out,
        incomplete=incomplete,
        python_modules=python_modules,
        native_extensions=native_extensions,
        loaded_libraries=loaded_libraries,
        qt_plugins=qt,
        event_counts=tuple(sorted(counts.items())),
        error=error,
    )


def write_trace(trace: RuntimeTrace, output: Path) -> Path:
    return write_trace_atomic(trace, output, bundle_root=None)


_REAL_VTK_TOKEN = re.compile(r"(?<!no)vtk", re.IGNORECASE)


def vtk_evidence(trace: RuntimeTrace) -> list[str]:
    """Return identities of any VTK-related evidence found in the trace.

    For PYTHON_MODULE/NATIVE_EXTENSION evidence, "VTK-related" means the dotted
    module name's root is literally ``vtk``/``vtkmodules`` — e.g. a module named
    ``cadquery.occ_impl.exporters.vtk`` (our own patched, VTK-free-until-called
    file) must NOT match just because "vtk" appears in its name/path. For
    DYLIB/FRAMEWORK evidence, the identity/path is checked with a real-token
    regex that excludes the "novtk" substring (from this PoC's own venv
    directory name, `.venv-novtk-poc`), matching the same false-positive fix
    applied in te001_run_all.py's OS-level lsof/vmmap scan.
    """
    hits: list[str] = []
    for item in (*trace.python_modules, *trace.native_extensions):
        if item.identity.split(".", 1)[0].lower() in {"vtk", "vtkmodules"}:
            hits.append(item.identity)
    for item in (*trace.loaded_libraries,):
        haystack = f"{item.identity} {item.bundle_relative_path or ''}"
        if _REAL_VTK_TOKEN.search(haystack):
            hits.append(item.identity)
    return hits
