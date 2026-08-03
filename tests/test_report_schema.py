import json
from pathlib import Path

from zerorod_analysis.deadlibs import DeadLibraryAnalysisResult
from zerorod_analysis.report import ReportEngine
from zerorod_analysis.report.models import REPORT_SCHEMA_ID, ReportRequest


def test_manifest_has_stable_schema_id_and_json_keeps_v2_schema(tmp_path: Path) -> None:
    engine = ReportEngine.default()
    result = DeadLibraryAnalysisResult()
    request = ReportRequest(tmp_path)

    manifest = engine.render(result, request)
    json_report = next(
        report for report in manifest.reports if report.relative_path.suffix == ".json"
    )

    assert manifest.schema == REPORT_SCHEMA_ID == "zerorod-analysis/report/v1"
    assert json.loads(json_report.content)["schema_version"] == 2
