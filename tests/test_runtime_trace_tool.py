from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.trace_runtime import main


def _app(tmp_path: Path, body: str) -> Path:
    bundle = tmp_path / "Fixture.app"
    executable = bundle / "Contents" / "MacOS" / "Fixture"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    executable.chmod(0o755)
    return bundle


def _manifest(bundle: Path) -> dict[str, str]:
    return {
        path.relative_to(bundle).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in bundle.rglob("*")
        if path.is_file()
    }


def test_controller_collects_and_cleans_raw_without_changing_bundle(tmp_path) -> None:
    app = _app(
        tmp_path,
        "printf '%s\\n' "
        '\'{"event":"start"}\' '
        '\'{"event":"audit-import","name":"dynamic_fixture","path":null}\' '
        '\'{"event":"end","errors":[]}\' '
        '> "$ZEROROD_RUNTIME_TRACE_RAW_PATH"\n',
    )
    before = _manifest(app)
    output = tmp_path / "trace.json"
    assert main([str(app), "--output", str(output), "--no-dyld", "--no-qt-debug"]) == 0
    payload = json.loads(output.read_text())
    assert payload["python_modules"][0]["identity"] == "dynamic_fixture"
    assert _manifest(app) == before
    assert not (tmp_path / "trace-raw").exists()


def test_keep_raw_and_incomplete_missing_end(tmp_path) -> None:
    app = _app(
        tmp_path,
        'printf \'%s\\n\' \'{"event":"start"}\' > "$ZEROROD_RUNTIME_TRACE_RAW_PATH"\n',
    )
    output = tmp_path / "trace.json"
    args = [str(app), "--output", str(output), "--keep-raw", "--no-dyld", "--no-qt-debug"]
    assert main(args) == 1
    assert json.loads(output.read_text())["incomplete"] is True
    assert (tmp_path / "trace-raw" / "hook.jsonl").is_file()


def test_failure_and_timeout_are_controlled(tmp_path) -> None:
    missing = tmp_path / "Missing.app"
    assert main([str(missing), "--output", str(tmp_path / "missing.json")]) == 2
    app = _app(tmp_path, "sleep 10\n")
    output = tmp_path / "timeout.json"
    args = [str(app), "--output", str(output), "--timeout", "0.1", "--no-dyld", "--no-qt-debug"]
    assert main(args) == 1
    payload = json.loads(output.read_text())
    assert payload["timed_out"] is True and payload["incomplete"] is True


def test_profiles_are_distinct_parser_choices() -> None:
    from tools.trace_runtime import build_parser

    parser = build_parser()
    for profile in ("startup-test", "preview-probe", "export-probe"):
        assert (
            parser.parse_args(["x.app", "--profile", profile, "--output", "x"]).profile == profile
        )
