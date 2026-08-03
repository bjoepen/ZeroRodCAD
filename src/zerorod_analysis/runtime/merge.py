"""Order-independent runtime evidence merging."""

from __future__ import annotations

from collections.abc import Iterable

from .models import EvidenceStatus, TraceEvidence

_STATUS_RANK = {
    EvidenceStatus.UNRESOLVED: 0,
    EvidenceStatus.INFERRED: 1,
    EvidenceStatus.OBSERVED: 2,
}


def evidence_sort_key(item: TraceEvidence) -> tuple[str, str, str]:
    return (item.kind.value, item.identity.casefold(), item.identity)


def merge_evidence(items: Iterable[TraceEvidence]) -> tuple[TraceEvidence, ...]:
    grouped: dict[tuple[str, str], list[TraceEvidence]] = {}
    for item in items:
        grouped.setdefault((item.kind.value, item.identity), []).append(item)
    merged: list[TraceEvidence] = []
    for values in grouped.values():
        exemplar = values[0]
        paths = sorted(
            {value.bundle_relative_path for value in values if value.bundle_relative_path}
        )
        details = {detail for value in values for detail in value.details}
        if len(paths) > 1:
            details.add("conflicting bundle paths: " + ", ".join(paths))
        merged.append(
            TraceEvidence(
                identity=exemplar.identity,
                kind=exemplar.kind,
                status=max(values, key=lambda value: _STATUS_RANK[value.status]).status,
                sources=tuple(sorted({source for value in values for source in value.sources})),
                event_count=sum(value.event_count for value in values),
                bundle_relative_path=paths[0] if paths else None,
                details=tuple(sorted(details)),
            )
        )
    return tuple(sorted(merged, key=evidence_sort_key))
