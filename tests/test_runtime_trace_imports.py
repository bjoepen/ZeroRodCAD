from __future__ import annotations

import importlib
import sys

from tools.trace_runtime import _read_raw

from zerorod_analysis.runtime.models import EvidenceKind


def test_static_and_dynamic_import_records_are_read(tmp_path) -> None:
    raw = tmp_path / "raw.jsonl"
    raw.write_text(
        '{"event":"audit-import","name":"json","path":null}\n'
        '{"event":"audit-import","name":"decimal","path":null}\n'
        '{"event":"end","errors":[]}\n',
        encoding="utf-8",
    )
    evidence, counts, ended, errors = _read_raw(raw, tmp_path / "Demo.app")
    assert {item.identity for item in evidence} == {"json", "decimal"}
    assert all(item.kind is EvidenceKind.PYTHON_MODULE for item in evidence)
    assert counts["audit-import"] == 2
    assert ended and not errors


def test_dynamic_import_stimulus_uses_runtime_name() -> None:
    module_name = "de" + "cimal"
    assert importlib.import_module(module_name) is sys.modules["decimal"]
