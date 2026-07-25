#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from tools.bundle_analyzer.scanner2 import (
    BundleSection,
    ScanFilter,
    Scanner,
    normalize_extensions,
    write_scanner_reports,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZeroRodCAD Build 019.1 – Scanner 2.0")
    parser.add_argument("app_bundle", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/reports/build-019.1-scanner2"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache/bundle-analyzer"),
    )
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--macho-only", action="store_true")
    parser.add_argument("--extensions", nargs="*", default=[])
    parser.add_argument(
        "--include-section",
        action="append",
        choices=[section.value for section in BundleSection],
        default=[],
    )
    parser.add_argument(
        "--exclude-section",
        action="append",
        choices=[section.value for section in BundleSection],
        default=[],
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    scan_filter = ScanFilter(
        include_sections=frozenset(BundleSection(value) for value in args.include_section),
        exclude_sections=frozenset(BundleSection(value) for value in args.exclude_section),
        extensions=normalize_extensions(args.extensions),
        macho_only=args.macho_only,
    )
    database = Scanner().scan(
        args.app_bundle,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        scan_filter=scan_filter,
    )
    write_scanner_reports(database, args.output_dir)

    statistics = database.statistics
    print("Build 019.1 – Scanner 2.0 abgeschlossen.")
    print(f"Dateien: {statistics.file_count}")
    print(f"Cache: {statistics.cache_hits} Treffer, {statistics.cache_misses} neu")
    print(f"Bericht: {args.output_dir / 'scanner2-report.md'}")
    print("Das App-Bundle wurde nicht verändert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
