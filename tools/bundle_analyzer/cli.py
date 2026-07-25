from __future__ import annotations

import argparse
from pathlib import Path

from .duplicates import duplicate_groups
from .planner import create_plan
from .report import write_reports
from .scanner import scan_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZeroRodCAD macOS Bundle Analyzer – Phase 5")
    parser.add_argument("app_bundle", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/reports/phase5-bundle-deduplication"),
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Erzeugt einen nicht-destruktiven Deduplizierungsplan.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    app_bundle = args.app_bundle.expanduser().resolve()

    files = scan_bundle(app_bundle)
    groups = duplicate_groups(files)
    actions = create_plan(groups)

    write_reports(
        output_dir=args.output_dir.resolve(),
        app_bundle=app_bundle,
        files=files,
        groups=groups,
        actions=actions,
    )

    print("Phase-5-Analyse abgeschlossen.")
    print(f"Bericht: {args.output_dir / 'phase5-deduplication-plan.md'}")
    print("Es wurden keine Dateien verändert.")
    return 0
