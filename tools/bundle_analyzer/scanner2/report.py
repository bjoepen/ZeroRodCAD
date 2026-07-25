from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .database import BundleDatabase


def human_size(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def write_scanner_reports(
    database: BundleDatabase,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    statistics = database.statistics

    payload = {
        "bundle": str(database.root),
        "statistics": asdict(statistics),
        "files": [
            {
                "relative_path": item.relative_path,
                "filename": item.filename,
                "extension": item.extension,
                "size_bytes": item.size_bytes,
                "sha256": item.sha256,
                "modified_ns": item.modified_ns,
                "inode": item.inode,
                "device": item.device,
                "is_symlink": item.is_symlink,
                "symlink_target": item.symlink_target,
                "section": item.section.value,
                "is_macho": item.is_macho,
                "architecture": list(item.architecture),
            }
            for item in database.files
        ],
    }
    inventory_path = output_dir / "scanner2-inventory.json"
    inventory_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Build 019.1a – Scanner 2.0 Report",
        "",
        f"- Bundle: `{database.root}`",
        f"- Dateien: **{statistics.file_count}**",
        f"- Verzeichnisse: **{statistics.directory_count}**",
        f"- Gesamtgröße: **{human_size(statistics.total_size_bytes)}**",
        f"- Symbolische Links: **{statistics.symlink_count}**",
        f"- Mach-O-Dateien: **{statistics.macho_count}**",
        f"- Python-Dateien: **{statistics.python_count}**",
        f"- Cache-Treffer: **{statistics.cache_hits}**",
        f"- Cache-Fehlschläge: **{statistics.cache_misses}**",
        "",
        "## Bundle-Bereiche",
        "",
        "| Bereich | Dateien | Größe |",
        "|---|---:|---:|",
    ]
    for section, count in statistics.section_counts.items():
        lines.append(f"| {section} | {count} | {human_size(statistics.section_sizes[section])} |")
    lines.extend(
        [
            "",
            "> Der Scanner arbeitet ausschließlich lesend. Das App-Bundle wurde nicht verändert.",
            "",
        ]
    )
    markdown_path = output_dir / "scanner2-report.md"
    markdown_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    return markdown_path, inventory_path
