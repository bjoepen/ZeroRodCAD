from pathlib import Path

from tools.trace_runtime import parse_qt_output

from zerorod_analysis.runtime.models import EvidenceKind


def test_qt_parser_only_accepts_successful_loads_and_tolerates_unknown_lines() -> None:
    fixture = Path(__file__).parent / "fixtures" / "runtime_trace" / "qt.txt"
    parsed = parse_qt_output(fixture.read_text(), Path("/Example.app"))
    assert len(parsed) == 1
    assert parsed[0].kind is EvidenceKind.QT_PLUGIN
    assert parsed[0].bundle_relative_path == "Contents/PlugIns/platforms/libqcocoa.dylib"
