#!/usr/bin/env python3
"""
ZeroRodCAD Bundle Analyzer

Analyzes native libraries inside a macOS .app bundle, with a focus on:

- Contents/Frameworks
- Contents/Resources
- Contents/Frameworks/vtkmodules/__dot__dylibs

Outputs:

- Markdown report
- CSV inventory
- JSON report
- Text lists for pairwise comparisons

The tool is read-only. It does not modify the app bundle.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class LibraryRecord:
    area: str
    relative_path: str
    basename: str
    size_bytes: int
    sha256: str
    inode: int
    device: int
    is_symlink: bool
    symlink_target: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze duplicate native libraries in a macOS .app bundle."
    )
    parser.add_argument(
        "app_bundle",
        type=Path,
        help='Path to the .app bundle, for example: "dist/ZeroRodCAD Desktop.app"',
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/reports/sprint3-phase4-bundle-analysis"),
        help="Directory for generated reports.",
    )
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=["*.dylib"],
        help='File patterns to include. Default: "*.dylib"',
    )
    parser.add_argument(
        "--include-so",
        action="store_true",
        help="Also include native Python extension modules (*.so).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Number of largest files/groups shown in the Markdown report.",
    )
    return parser.parse_args()


def human_size(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def find_matching_files(directory: Path, patterns: list[str]) -> list[Path]:
    if not directory.exists():
        return []

    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in directory.rglob(pattern) if path.is_file())
    return sorted(files)


def collect_area(
    app_bundle: Path,
    area_name: str,
    directory: Path,
    patterns: list[str],
    excluded_roots: Iterable[Path] = (),
) -> list[LibraryRecord]:
    excluded_roots = tuple(path.resolve() for path in excluded_roots)
    records: list[LibraryRecord] = []

    for path in find_matching_files(directory, patterns):
        resolved_parent = path.parent.resolve()
        if any(
            root == resolved_parent or root in resolved_parent.parents for root in excluded_roots
        ):
            continue

        try:
            stat = path.stat()
            is_symlink = path.is_symlink()
            symlink_target = os.readlink(path) if is_symlink else None
            records.append(
                LibraryRecord(
                    area=area_name,
                    relative_path=str(path.relative_to(app_bundle)),
                    basename=path.name,
                    size_bytes=stat.st_size,
                    sha256=sha256_file(path),
                    inode=stat.st_ino,
                    device=stat.st_dev,
                    is_symlink=is_symlink,
                    symlink_target=symlink_target,
                )
            )
        except OSError as exc:
            print(f"WARNING: Could not inspect {path}: {exc}", file=sys.stderr)

    return records


def group_by(records: list[LibraryRecord], attribute: str) -> dict[str, list[LibraryRecord]]:
    result: dict[str, list[LibraryRecord]] = defaultdict(list)
    for record in records:
        result[str(getattr(record, attribute))].append(record)
    return dict(result)


def area_summary(records: list[LibraryRecord]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    areas = sorted({record.area for record in records})
    for area in areas:
        area_records = [record for record in records if record.area == area]
        summary[area] = {
            "file_count": len(area_records),
            "total_size_bytes": sum(record.size_bytes for record in area_records),
            "unique_hash_count": len({record.sha256 for record in area_records}),
            "unique_basename_count": len({record.basename for record in area_records}),
        }
    return summary


def duplicate_hash_groups(records: list[LibraryRecord]) -> list[list[LibraryRecord]]:
    groups = [group for group in group_by(records, "sha256").values() if len(group) > 1]
    return sorted(
        groups,
        key=lambda group: (group[0].size_bytes * (len(group) - 1), group[0].basename),
        reverse=True,
    )


def duplicate_basename_groups(records: list[LibraryRecord]) -> list[list[LibraryRecord]]:
    groups = [group for group in group_by(records, "basename").values() if len(group) > 1]
    return sorted(groups, key=lambda group: group[0].basename.lower())


def area_records(records: list[LibraryRecord], area: str) -> list[LibraryRecord]:
    return [record for record in records if record.area == area]


def compare_areas(
    records: list[LibraryRecord],
    first: str,
    second: str,
) -> dict[str, object]:
    left = area_records(records, first)
    right = area_records(records, second)

    left_names = {record.basename for record in left}
    right_names = {record.basename for record in right}
    left_hashes = {record.sha256 for record in left}
    right_hashes = {record.sha256 for record in right}

    left_by_name = {record.basename: record for record in left}
    right_by_name = {record.basename: record for record in right}

    common_names = sorted(left_names & right_names)
    same_name_same_hash = sorted(
        name for name in common_names if left_by_name[name].sha256 == right_by_name[name].sha256
    )
    same_name_different_hash = sorted(
        name for name in common_names if left_by_name[name].sha256 != right_by_name[name].sha256
    )

    return {
        "first": first,
        "second": second,
        "only_first_names": sorted(left_names - right_names),
        "only_second_names": sorted(right_names - left_names),
        "common_names": common_names,
        "same_name_same_hash": same_name_same_hash,
        "same_name_different_hash": same_name_different_hash,
        "only_first_hashes": sorted(left_hashes - right_hashes),
        "only_second_hashes": sorted(right_hashes - left_hashes),
        "common_hashes": sorted(left_hashes & right_hashes),
    }


def write_csv(path: Path, records: list[LibraryRecord]) -> None:
    fieldnames = (
        list(asdict(records[0]).keys())
        if records
        else [
            "area",
            "relative_path",
            "basename",
            "size_bytes",
            "sha256",
            "inode",
            "device",
            "is_symlink",
            "symlink_target",
        ]
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def write_lines(path: Path, values: Iterable[str]) -> None:
    path.write_text("\n".join(values) + "\n", encoding="utf-8")


def render_markdown(
    app_bundle: Path,
    records: list[LibraryRecord],
    summary: dict[str, dict[str, int]],
    comparisons: list[dict[str, object]],
    top: int,
) -> str:
    duplicate_hashes = duplicate_hash_groups(records)
    duplicate_names = duplicate_basename_groups(records)

    physical_total = sum(record.size_bytes for record in records)
    unique_by_hash = {}
    for record in records:
        unique_by_hash.setdefault(record.sha256, record)
    unique_total = sum(record.size_bytes for record in unique_by_hash.values())
    theoretical_duplicate_bytes = physical_total - unique_total

    lines: list[str] = []
    lines.append("# ZeroRodCAD Bundle Analysis")
    lines.append("")
    lines.append(f"- App bundle: `{app_bundle}`")
    lines.append(f"- Analysierte Dateien: **{len(records)}**")
    lines.append(f"- Physische Gesamtgröße: **{human_size(physical_total)}**")
    lines.append(f"- Größe eindeutiger Inhalte nach SHA256: **{human_size(unique_total)}**")
    lines.append(
        "- Theoretisch durch byteidentische Mehrfachkopien belegter Speicher: "
        f"**{human_size(theoretical_duplicate_bytes)}**"
    )
    lines.append("")
    lines.append(
        "> Hinweis: Der theoretische Wert ist kein Löschvorschlag. "
        "Er zeigt nur, wie viel Inhalt mehrfach vorhanden ist."
    )
    lines.append("")

    lines.append("## Bereiche")
    lines.append("")
    lines.append("| Bereich | Dateien | Größe | Eindeutige Hashes | Eindeutige Namen |")
    lines.append("|---|---:|---:|---:|---:|")
    for area, data in summary.items():
        lines.append(
            f"| `{area}` | {data['file_count']} | "
            f"{human_size(data['total_size_bytes'])} | "
            f"{data['unique_hash_count']} | {data['unique_basename_count']} |"
        )
    lines.append("")

    lines.append("## Paarweise Vergleiche")
    lines.append("")
    for comparison in comparisons:
        first = str(comparison["first"])
        second = str(comparison["second"])
        lines.append(f"### `{first}` ↔ `{second}`")
        lines.append("")
        lines.append(
            f"- Nur in `{first}` nach Dateiname: **{len(comparison['only_first_names'])}**"
        )
        lines.append(
            f"- Nur in `{second}` nach Dateiname: **{len(comparison['only_second_names'])}**"
        )
        lines.append(f"- Gemeinsame Dateinamen: **{len(comparison['common_names'])}**")
        lines.append(
            f"- Gleicher Name und gleicher Hash: **{len(comparison['same_name_same_hash'])}**"
        )
        lines.append(
            f"- Gleicher Name, aber anderer Hash: **{len(comparison['same_name_different_hash'])}**"
        )
        lines.append(f"- Gemeinsame SHA256-Inhalte: **{len(comparison['common_hashes'])}**")
        lines.append("")

        different = list(comparison["same_name_different_hash"])
        if different:
            lines.append("Dateien mit gleichem Namen, aber unterschiedlichem Inhalt:")
            lines.append("")
            for name in different[:top]:
                lines.append(f"- `{name}`")
            if len(different) > top:
                lines.append(f"- … {len(different) - top} weitere")
            lines.append("")

    lines.append("## Größte byteidentische Duplikatgruppen")
    lines.append("")
    if not duplicate_hashes:
        lines.append("Keine byteidentischen Duplikate gefunden.")
    else:
        lines.append("| Inhalt | Einzelgröße | Kopien | Mehrfach belegter Speicher | Fundorte |")
        lines.append("|---|---:|---:|---:|---|")
        for group in duplicate_hashes[:top]:
            single_size = group[0].size_bytes
            waste = single_size * (len(group) - 1)
            locations = "<br>".join(f"`{record.relative_path}`" for record in group)
            lines.append(
                f"| `{group[0].sha256[:12]}…` | {human_size(single_size)} | "
                f"{len(group)} | {human_size(waste)} | {locations} |"
            )
    lines.append("")

    lines.append("## Größte Einzeldateien")
    lines.append("")
    lines.append("| Größe | Bereich | Datei |")
    lines.append("|---:|---|---|")
    for record in sorted(records, key=lambda item: item.size_bytes, reverse=True)[:top]:
        lines.append(
            f"| {human_size(record.size_bytes)} | `{record.area}` | `{record.relative_path}` |"
        )
    lines.append("")

    lines.append("## Mehrfach vorkommende Dateinamen")
    lines.append("")
    lines.append(f"Gefundene Gruppen: **{len(duplicate_names)}**")
    lines.append("")
    for group in duplicate_names[:top]:
        hashes = {record.sha256 for record in group}
        status = "byteidentisch" if len(hashes) == 1 else "unterschiedlicher Inhalt"
        lines.append(f"- `{group[0].basename}` — {len(group)} Vorkommen, {status}")
    if len(duplicate_names) > top:
        lines.append(f"- … {len(duplicate_names) - top} weitere Gruppen")
    lines.append("")

    lines.append("## Bewertungshinweise")
    lines.append("")
    lines.append(
        "- Byteidentische Dateien sind echte Inhaltsduplikate, können aber dennoch "
        "durch Loader-Pfade, Codesigning oder PyInstaller-Strukturen erforderlich sein."
    )
    lines.append(
        "- Dateien mit gleichem Namen und unterschiedlichem Hash dürfen nicht als "
        "austauschbar betrachtet werden."
    )
    lines.append(
        "- Vor jeder Deduplizierung muss geprüft werden, welche Pfade die nativen "
        "Erweiterungsmodule mit `otool -L` und `@rpath` tatsächlich auflösen."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    app_bundle = args.app_bundle.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not app_bundle.exists():
        print(f"ERROR: App bundle not found: {app_bundle}", file=sys.stderr)
        return 2

    contents = app_bundle / "Contents"
    if not contents.is_dir():
        print(f"ERROR: Not a valid macOS app bundle: {app_bundle}", file=sys.stderr)
        return 2

    patterns = list(args.patterns)
    if args.include_so and "*.so" not in patterns:
        patterns.append("*.so")

    frameworks = contents / "Frameworks"
    resources = contents / "Resources"
    dot_dylibs = frameworks / "vtkmodules" / "__dot__dylibs"

    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[LibraryRecord] = []
    records.extend(
        collect_area(
            app_bundle,
            "Frameworks-root",
            frameworks,
            patterns,
            excluded_roots=(dot_dylibs,),
        )
    )
    records.extend(
        collect_area(
            app_bundle,
            "Resources",
            resources,
            patterns,
        )
    )
    records.extend(
        collect_area(
            app_bundle,
            "VTK-__dot__dylibs",
            dot_dylibs,
            patterns,
        )
    )

    records = sorted(records, key=lambda record: (record.area, record.relative_path))
    summary = area_summary(records)

    area_names = ["Frameworks-root", "Resources", "VTK-__dot__dylibs"]
    comparisons = [
        compare_areas(records, area_names[index], area_names[other])
        for index in range(len(area_names))
        for other in range(index + 1, len(area_names))
    ]

    write_csv(output_dir / "bundle-inventory.csv", records)

    json_report = {
        "app_bundle": str(app_bundle),
        "patterns": patterns,
        "summary": summary,
        "comparisons": comparisons,
        "records": [asdict(record) for record in records],
    }
    (output_dir / "bundle-analysis.json").write_text(
        json.dumps(json_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown = render_markdown(
        app_bundle=app_bundle,
        records=records,
        summary=summary,
        comparisons=comparisons,
        top=max(1, args.top),
    )
    (output_dir / "bundle-analysis.md").write_text(markdown, encoding="utf-8")

    for area in area_names:
        safe_name = area.lower().replace("_", "-")
        current = area_records(records, area)
        write_lines(
            output_dir / f"{safe_name}-names.txt",
            sorted(record.basename for record in current),
        )
        write_lines(
            output_dir / f"{safe_name}-hashes.txt",
            sorted(record.sha256 for record in current),
        )

    for comparison in comparisons:
        first = str(comparison["first"]).lower().replace("_", "-")
        second = str(comparison["second"]).lower().replace("_", "-")
        prefix = output_dir / f"{first}--vs--{second}"

        write_lines(
            Path(f"{prefix}--same-name-same-hash.txt"),
            comparison["same_name_same_hash"],
        )
        write_lines(
            Path(f"{prefix}--same-name-different-hash.txt"),
            comparison["same_name_different_hash"],
        )
        write_lines(
            Path(f"{prefix}--only-first.txt"),
            comparison["only_first_names"],
        )
        write_lines(
            Path(f"{prefix}--only-second.txt"),
            comparison["only_second_names"],
        )

    print("Bundle analysis complete.")
    print(f"App bundle : {app_bundle}")
    print(f"Files      : {len(records)}")
    print(f"Report     : {output_dir / 'bundle-analysis.md'}")
    print(f"CSV        : {output_dir / 'bundle-inventory.csv'}")
    print(f"JSON       : {output_dir / 'bundle-analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
