from pathlib import Path

from tools.trace_runtime import _read_raw, parse_dyld_output

from zerorod_analysis.runtime.models import EvidenceKind

FIXTURES = Path(__file__).parent / "fixtures" / "runtime_trace"


def test_native_extension_is_classified(tmp_path) -> None:
    raw = tmp_path / "raw.jsonl"
    raw.write_text(
        '{"event":"module-snapshot","phase":"end","name":"_json",'
        '"path":"/Example.app/Contents/MacOS/_json.cpython-313-darwin.so"}\n'
        '{"event":"end","errors":[]}\n',
        encoding="utf-8",
    )
    evidence, _, _, _ = _read_raw(raw, Path("/Example.app"))
    assert evidence[0].kind is EvidenceKind.NATIVE_EXTENSION


def test_dyld_dylib_and_framework_parser() -> None:
    parsed = parse_dyld_output((FIXTURES / "dyld.txt").read_text(), Path("/Example.app"))
    assert {item.kind for item in parsed} == {EvidenceKind.DYLIB, EvidenceKind.FRAMEWORK}
