from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import BundleFile, DuplicateGroup
from .planner import DeduplicationAction


def human_size(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def write_reports(
    output_dir: Path,
    app_bundle: Path,
    files: list[BundleFile],
    groups: list[DuplicateGroup],
    actions: list[DeduplicationAction],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    physical = sum(item.size_bytes for item in files)
    redundant = sum(group.redundant_bytes for group in groups)

    data = {
        "app_bundle": str(app_bundle),
        "file_count": len(files),
        "physical_size_bytes": physical,
        "redundant_bytes": redundant,
        "duplicate_groups": [
            {
                "sha256": group.sha256,
                "size_bytes": group.size_bytes,
                "redundant_bytes": group.redundant_bytes,
                "files": [item.relative_path for item in group.files],
            }
            for group in groups
        ],
        "plan": [asdict(action) for action in actions],
    }
    (output_dir / "phase5-deduplication-plan.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Phase 5 – Bundle Deduplication Plan",
        "",
        f"- App-Bundle: `{app_bundle}`",
        f"- Analysierte native Dateien: **{len(files)}**",
        f"- Physische Größe: **{human_size(physical)}**",
        f"- Byteidentischer redundanter Inhalt: **{human_size(redundant)}**",
        f"- Duplikatgruppen: **{len(groups)}**",
        "",
        "> Dieser Bericht ist ein Dry-Run. Es werden keine Bundle-Dateien verändert.",
        "",
        "## Sicherheitsstatus",
        "",
        "Die automatische Entfernung ist in Phase 5.1 bewusst gesperrt. "
        "Jede Gruppe muss zuerst durch Loader-, Start-, Preview-, STL- und "
        "STEP-Tests validiert werden.",
        "",
        "## Größte Duplikatgruppen",
        "",
        "| Redundant | Einzelgröße | Kopien | Kanonische Datei |",
        "|---:|---:|---:|---|",
    ]

    for group, action in zip(groups[:40], actions[:40], strict=False):
        lines.append(
            f"| {human_size(group.redundant_bytes)} | {human_size(group.size_bytes)} | "
            f"{len(group.files)} | `{Path(action.keep).name}` |"
        )

    lines.extend(
        [
            "",
            "## Nächster Schritt",
            "",
            "1. Plan mit `--plan` erzeugen.",
            "2. Für die größten Gruppen die tatsächlichen Loader-Pfade prüfen.",
            "3. Eine einzige Duplikatklasse in einer Testkopie ersetzen.",
            "4. Codesignatur erneuern.",
            "5. vollständige Validierung ausführen.",
            "6. Erst danach schrittweise erweitern.",
            "",
        ]
    )

    (output_dir / "phase5-deduplication-plan.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
