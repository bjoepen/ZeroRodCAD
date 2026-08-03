"""Report generation for dead-library analysis results."""

from __future__ import annotations

from pathlib import Path

from ..scanner.report import human_size
from .advisor import Advice, BundleHealth, BundleHealthEvaluator, RecommendationAdvisor
from .models import DeadLibraryAnalysisResult, DeadLibraryFinding, Recommendation
from .size import compute_savings, summarize_sizes


def _reference_payload(finding: DeadLibraryFinding) -> list[dict[str, str]]:
    return [
        {
            "source": reference.source,
            "target": reference.target,
            "kind": reference.kind.value,
            "detail": reference.detail,
        }
        for reference in finding.usage.references
    ]


def _health(result: DeadLibraryAnalysisResult) -> BundleHealth:
    return result.bundle_health or BundleHealthEvaluator().evaluate(result)


def _advice_map(result: DeadLibraryAnalysisResult) -> dict[int, Advice]:
    if result.advisor_results is not None:
        return {
            id(finding): advice
            for finding, advice in zip(result.findings, result.advisor_results, strict=True)
        }
    advisor = RecommendationAdvisor()
    return {id(finding): advisor.advise(finding) for finding in result.findings}


def result_payload(result: DeadLibraryAnalysisResult) -> dict[str, object]:
    """Return the canonical, JSON-serializable representation of a result."""

    size_summary = summarize_sizes(result)
    savings = compute_savings(result.findings)
    advice_by_finding = _advice_map(result)
    health = _health(result)
    findings = []
    for finding in result.findings:
        advice = advice_by_finding[id(finding)]
        findings.append(
            {
                "library_id": finding.library.identifier,
                "paths": [path.as_posix() for path in finding.library.paths],
                "size_bytes": finding.library.size_bytes,
                "library_category": finding.library.category.value,
                "finding_category": finding.category.value,
                "confidence": finding.confidence.value,
                "recommendation": advice.recommendation.value,
                "risk_score": advice.risk_score,
                "risk_label": advice.risk_label,
                "reasons": list(advice.reasons),
                "actions": list(advice.actions),
                "references": _reference_payload(finding),
                "unresolved_hints": list(finding.usage.unresolved_hints),
            }
        )
    return {
        "schema_version": 2,
        "bundle_root": str(result.bundle_root) if result.bundle_root is not None else None,
        "bundle_health": {
            "score": health.score,
            "grade": health.grade,
            "deductions": list(health.deductions),
        },
        "summary": {
            "finding_count": len(result.findings),
            "total_bundle_size_bytes": result.total_bundle_size_bytes,
            "total_library_size_bytes": size_summary.total_library_bytes,
            "potential_savings_bytes": size_summary.potential_savings_bytes,
            "safe_remove_count": size_summary.safe_remove_count,
            "review_count": sum(
                finding.recommendation is Recommendation.REVIEW for finding in result.findings
            ),
            "keep_count": sum(
                finding.recommendation is Recommendation.KEEP for finding in result.findings
            ),
        },
        "potential_savings": [
            {"library_id": identifier, "size_bytes": size} for identifier, size in savings.entries
        ],
        "findings": findings,
    }


def _recommendation_title(value: Recommendation) -> str:
    return {
        Recommendation.SAFE_REMOVE: "SAFE REMOVE",
        Recommendation.REVIEW: "REVIEW",
        Recommendation.KEEP: "KEEP",
    }[value]


def _findings_table(
    findings: list[DeadLibraryFinding], advice_by_finding: dict[int, Advice]
) -> list[str]:
    lines = [
        "| Empfehlung | Bibliothek | Größe | Risiko | Konfidenz | Begründung |",
        "|---|---|---:|---:|---|---|",
    ]
    for finding in findings:
        advice = advice_by_finding[id(finding)]
        reasons = "<br>".join(advice.reasons) or "Keine Begründung verfügbar."
        lines.append(
            f"| {_recommendation_title(advice.recommendation)} | "
            f"`{finding.library.identifier}` | {human_size(finding.library.size_bytes)} | "
            f"{advice.risk_score}/100 | {finding.confidence.value.upper()} | {reasons} |"
        )
    return lines


def dead_libraries_markdown(result: DeadLibraryAnalysisResult) -> str:
    summary = summarize_sizes(result)
    health = _health(result)
    advice_by_finding = _advice_map(result)
    review_count = sum(item.recommendation is Recommendation.REVIEW for item in result.findings)
    keep_count = sum(item.recommendation is Recommendation.KEEP for item in result.findings)
    ordered = sorted(
        result.findings,
        key=lambda finding: (
            {Recommendation.SAFE_REMOVE: 0, Recommendation.REVIEW: 1, Recommendation.KEEP: 2}[
                finding.recommendation
            ],
            -finding.library.size_bytes,
            finding.library.identifier.casefold(),
        ),
    )
    lines = [
        "# Dead-Library-Analyse",
        "",
        f"- Bundle: `{result.bundle_root}`",
        f"- Bundle Health: **{health.score}/100 ({health.grade})**",
        f"- Analysierte Bibliothekseinheiten: **{len(result.findings)}**",
        f"- Potenzielle Einsparung: **{human_size(summary.potential_savings_bytes)}**",
        f"- SAFE REMOVE: **{summary.safe_remove_count}**",
        f"- REVIEW: **{review_count}**",
        f"- KEEP: **{keep_count}**",
        "",
        "## Findings",
        "",
        *_findings_table(ordered, advice_by_finding),
        "",
        "> SAFE REMOVE ist eine statische Analyseempfehlung. Vor dem Löschen muss "
        "ein reproduzierbarer Bundle-Test durchgeführt werden.",
        "",
    ]
    return "\n".join(lines)


def bundle_size_markdown(result: DeadLibraryAnalysisResult) -> str:
    summary = summarize_sizes(result)
    savings = compute_savings(result.findings)
    lines = [
        "# Bundle Size Analysis",
        "",
        f"- Bundle-Größe: **{human_size(result.total_bundle_size_bytes)}**",
        f"- Erkannte Bibliotheken: **{human_size(summary.total_library_bytes)}**",
        f"- Potenzielle Einsparung: **{human_size(summary.potential_savings_bytes)}**",
        "",
        "## Kandidaten nach Einsparpotenzial",
        "",
        "| Bibliothek | Größe |",
        "|---|---:|",
    ]
    if savings.entries:
        lines.extend(
            f"| `{identifier}` | {human_size(size)} |" for identifier, size in savings.entries
        )
    else:
        lines.append("| _Keine SAFE-REMOVE-Kandidaten_ | 0 B |")
    lines.append("")
    return "\n".join(lines)


def optimization_markdown(result: DeadLibraryAnalysisResult) -> str:
    advice_by_finding = _advice_map(result)
    health = _health(result)
    groups = {
        recommendation: [
            finding for finding in result.findings if finding.recommendation is recommendation
        ]
        for recommendation in Recommendation
    }
    lines = [
        "# Optimization Report",
        "",
        f"Bundle Health: **{health.score}/100 ({health.grade})**",
        "",
        "## Entscheidungsreihenfolge",
        "",
        "1. SAFE-REMOVE-Kandidaten in einer Kopie des Bundles entfernen.",
        "2. Anwendung starten und die betroffenen Funktionsbereiche testen.",
        "3. REVIEW-Kandidaten nur nach zusätzlicher Laufzeitanalyse bewerten.",
        "4. KEEP-Einträge nicht entfernen.",
        "",
    ]
    for recommendation in (
        Recommendation.SAFE_REMOVE,
        Recommendation.REVIEW,
        Recommendation.KEEP,
    ):
        findings = sorted(
            groups[recommendation],
            key=lambda finding: (
                -finding.library.size_bytes,
                finding.library.identifier.casefold(),
            ),
        )
        lines.extend([f"## {_recommendation_title(recommendation)}", ""])
        if not findings:
            lines.extend(["_Keine Einträge._", ""])
            continue
        for finding in findings:
            advice = advice_by_finding[id(finding)]
            lines.append(
                f"### `{finding.library.identifier}` — {human_size(finding.library.size_bytes)}"
            )
            lines.extend(["", f"Risk Score: **{advice.risk_score}/100 ({advice.risk_label})**", ""])
            lines.extend(f"- {reason}" for reason in advice.reasons)
            if finding.usage.references:
                lines.append(f"- Referenzen: {len(finding.usage.references)}")
            lines.extend(["", "Empfohlene Schritte:", ""])
            lines.extend(f"1. {action}" for action in advice.actions)
            lines.append("")
    return "\n".join(lines)


def optimization_plan_markdown(result: DeadLibraryAnalysisResult) -> str:
    advice_by_finding = _advice_map(result)
    health = _health(result)
    ordered = sorted(
        result.findings,
        key=lambda finding: (
            {Recommendation.SAFE_REMOVE: 0, Recommendation.REVIEW: 1, Recommendation.KEEP: 2}[
                finding.recommendation
            ],
            advice_by_finding[id(finding)].risk_score,
            -finding.library.size_bytes,
            finding.library.identifier.casefold(),
        ),
    )
    lines = [
        "# Optimization Plan",
        "",
        f"Bundle Health: **{health.score}/100 ({health.grade})**",
        "",
    ]
    if health.deductions:
        lines.extend(["## Health deductions", "", *(f"- {item}" for item in health.deductions), ""])
    lines.extend(["## Priorisierte Maßnahmen", ""])
    if not ordered:
        lines.extend(["_Keine Maßnahmen erforderlich._", ""])
        return "\n".join(lines)

    for index, finding in enumerate(ordered, start=1):
        advice = advice_by_finding[id(finding)]
        lines.extend(
            [
                f"### {index}. {_recommendation_title(advice.recommendation)}: "
                f"`{finding.library.identifier}`",
                "",
                f"- Größe: **{human_size(finding.library.size_bytes)}**",
                f"- Risk Score: **{advice.risk_score}/100 ({advice.risk_label})**",
                *[f"- {reason}" for reason in advice.reasons],
                "",
                *[f"{step}. {action}" for step, action in enumerate(advice.actions, start=1)],
                "",
            ]
        )
    return "\n".join(lines)


def write_dead_library_reports(
    result: DeadLibraryAnalysisResult,
    output_dir: Path,
) -> tuple[Path, Path, Path, Path, Path]:
    """Write the canonical JSON report and its Markdown projections."""

    from ..report import ReportEngine, ReportRequest

    paths = ReportEngine.default().generate(result, ReportRequest(output_directory=output_dir))
    return paths  # type: ignore[return-value]
