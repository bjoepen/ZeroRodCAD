"""Runtime adjustments for the frozen macOS bundle."""

from __future__ import annotations

import atexit
import json
import os
import sys
from pathlib import Path

from zerorod_analysis.runtime.schema import (
    PROFILE_ERROR_PROBE,
    PROFILE_EXPORT_PROBE,
    PROFILE_PREVIEW_ALT_PROBE,
    PROFILE_PREVIEW_PROBE,
    TRACE_BUNDLE_ROOT_ENV,
    TRACE_ENABLE_ENV,
    TRACE_PROFILE_ENV,
    TRACE_RAW_PATH_ENV,
    TRACE_STIMULUS_DIR_ENV,
)

if getattr(sys, "frozen", False):
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    plugin_root = bundle_root / "PySide6" / "Qt" / "plugins"
    if plugin_root.exists():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_root))


class _RuntimeRecorder:
    """Process-local raw recorder; normalization belongs to the controller."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.errors: list[str] = []

    def write(self, event: str, **payload: object) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"event": event, **payload}, sort_keys=True) + "\n")
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            if message not in self.errors:
                self.errors.append(message)

    def snapshot(self, phase: str) -> None:
        for name, module in sorted(sys.modules.items()):
            self.write(
                "module-snapshot",
                phase=phase,
                name=name,
                path=getattr(module, "__file__", None),
                loader=type(getattr(module, "__loader__", None)).__name__,
            )

    def audit(self, event: str, args: tuple[object, ...]) -> None:
        if event == "import":
            self.write(
                "audit-import",
                name=str(args[0]) if args else "",
                path=str(args[1]) if len(args) > 1 and args[1] else None,
            )
        elif event in {"ctypes.dlopen", "ctypes.dlsym"}:
            self.write("audit-native-load", audit_event=event, value=str(args[0]) if args else "")


def _run_trace_stimulus(recorder: _RuntimeRecorder) -> None:
    from zerorod_analysis.runtime.schema import TRACE_PROFILES

    profile = os.environ.get(TRACE_PROFILE_ENV, TRACE_PROFILES[0])
    try:
        if profile == PROFILE_PREVIEW_PROBE:
            from zerorodcad.parameters import ZeroRodParameters
            from zerorodcad.preview import build_preview_scene

            scene = build_preview_scene(ZeroRodParameters())
            if not scene.meshes:
                raise RuntimeError("preview stimulus returned no meshes")
        elif profile == PROFILE_EXPORT_PROBE:
            from zerorodcad.export import export_project
            from zerorodcad.parameters import ZeroRodParameters

            output = Path(os.environ[TRACE_STIMULUS_DIR_ENV])
            created = export_project(output, ZeroRodParameters())
            if not created or any(not path.is_file() for path in created):
                raise RuntimeError("export stimulus did not create all expected files")
        elif profile == PROFILE_PREVIEW_ALT_PROBE:
            # Same alternate parameter set already proven valid by
            # tests/test_preview.py::test_virtual_strings_follow_string_count
            # (4 strings instead of the default 3) — not a new geometry
            # assumption, just exercised here for import/dependency evidence.
            from zerorodcad.parameters import ZeroRodParameters
            from zerorodcad.preview import build_preview_scene

            alt_params = ZeroRodParameters(
                string_gauges_inch=(0.040, 0.030, 0.020, 0.012),
                string_spacing=8.0,
            )
            scene = build_preview_scene(alt_params)
            if not scene.meshes:
                raise RuntimeError("preview-alt stimulus returned no meshes")
        elif profile == PROFILE_ERROR_PROBE:
            # Same invalid parameter set already proven to raise ValueError by
            # tests/test_export.py::test_export_rejects_invalid_parameters —
            # exercises the validation error path, not a real failure.
            from zerorodcad.export import export_project
            from zerorodcad.parameters import ZeroRodParameters

            output = Path(os.environ[TRACE_STIMULUS_DIR_ENV])
            invalid_params = ZeroRodParameters(body_width=0)
            try:
                export_project(output, invalid_params)
            except ValueError as exc:
                recorder.write("stimulus-expected-error", profile=profile, message=str(exc))
            else:
                raise RuntimeError("error-probe stimulus did not raise ValueError as expected")
        recorder.write("stimulus-complete", profile=profile)
    except Exception as exc:
        recorder.write("recorder-error", message=f"stimulus: {type(exc).__name__}: {exc}")


def _enable_runtime_trace() -> None:
    raw_value = os.environ.get(TRACE_RAW_PATH_ENV)
    if not raw_value:
        return
    raw_path = Path(raw_value)
    recorder = _RuntimeRecorder(raw_path)
    try:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        recorder.write(
            "start",
            bundle_root=os.environ.get(TRACE_BUNDLE_ROOT_ENV),
            profile=os.environ.get(TRACE_PROFILE_ENV),
        )
        recorder.snapshot("start")
        sys.addaudithook(recorder.audit)

        def finish() -> None:
            recorder.snapshot("end")
            recorder.write("end", errors=recorder.errors)

        atexit.register(finish)
        atexit.register(_run_trace_stimulus, recorder)
    except Exception as exc:
        recorder.write("recorder-error", message=f"setup: {type(exc).__name__}: {exc}")


if os.environ.get(TRACE_ENABLE_ENV):
    _enable_runtime_trace()
