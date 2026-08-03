from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from zerorod_analysis.build_metadata import BUILD_ID
from zerorod_analysis.runtime.models import EvidenceKind, RuntimeTrace, TraceEvidence
from zerorod_analysis.runtime.schema import TRACE_SCHEMA_ID
from zerorod_analysis.runtime.serialization import trace_json_bytes


def _trace() -> RuntimeTrace:
    evidence = TraceEvidence("example", EvidenceKind.PYTHON_MODULE, sources=("audit",))
    return RuntimeTrace(
        schema=TRACE_SCHEMA_ID,
        build_id=BUILD_ID,
        python_version="3.13",
        platform="darwin",
        started_at="2026-08-03T10:00:00Z",
        ended_at="2026-08-03T10:00:01Z",
        profile="startup-test",
        exit_status="exited",
        exit_code=0,
        timed_out=False,
        incomplete=False,
        python_modules=(evidence,),
    )


def test_schema_build_and_serialization_are_stable() -> None:
    assert TRACE_SCHEMA_ID == "zerorod-analysis/runtime-trace/v1"
    assert BUILD_ID == "021-M1"
    assert trace_json_bytes(_trace()) == trace_json_bytes(_trace())


def test_models_are_immutable_and_validate_counts() -> None:
    evidence = TraceEvidence("x", EvidenceKind.PYTHON_MODULE)
    with pytest.raises(FrozenInstanceError):
        evidence.identity = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="positive"):
        TraceEvidence("x", EvidenceKind.PYTHON_MODULE, event_count=0)
