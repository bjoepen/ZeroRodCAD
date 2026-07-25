#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Direct execution (``python tools/scan_bundle.py``) places ``tools`` on
# sys.path, not the repository root. Add the root before importing the package.
if __package__ in {None, ""}:
    repository_root = Path(__file__).resolve().parents[1]
    root_text = str(repository_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

from tools.bundle_analyzer.scanner2 import (  # noqa: E402
    BundleSection,
    ScanFilter,
    Scanner,
    normalize_extensions,
    write_scanner_reports,
)

BUILD_VERSION = "019.2"
LOGGER = logging.getLogger("zerorodcad.scanner2")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("ZeroRodCAD Build 019.2 – Scanner 2.0 with Mach-O dependency analysis")
    )
    parser.add_argument("app_bundle", type=Path, help="Path to the macOS .app bundle")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/reports/build-019.2"),
        help="Directory for Markdown and JSON reports",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache/bundle-analyzer"),
        help="Directory for Scanner 2.0 cache files",
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable cache reads and writes")
    parser.add_argument("--macho-only", action="store_true", help="Include Mach-O objects only")
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=[],
        metavar="EXT",
        help="Include only these extensions, for example dylib so",
    )
    parser.add_argument(
        "--include-section",
        action="append",
        choices=[section.value for section in BundleSection],
        default=[],
        help="Include a bundle section; may be supplied repeatedly",
    )
    parser.add_argument(
        "--exclude-section",
        action="append",
        choices=[section.value for section in BundleSection],
        default=[],
        help="Exclude a bundle section; may be supplied repeatedly",
    )
    parser.add_argument(
        "--macho-dependencies",
        action="store_true",
        help="Analyze Mach-O dependencies with otool and write graph reports",
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--verbose", action="store_true", help="Enable detailed logging")
    verbosity.add_argument("--quiet", action="store_true", help="Suppress normal status output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {BUILD_VERSION}")
    return parser


def configure_logging(*, verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def main(argv: list[str] | None = None) -> int:
    effective_argv = sys.argv[1:] if argv is None else argv

    if effective_argv == ["--version"]:
        print(f"ZeroRodCAD Scanner 2.0 – Build {BUILD_VERSION}")
        return 0
    args = build_parser().parse_args(effective_argv)
    configure_logging(verbose=args.verbose, quiet=args.quiet)

    scan_filter = ScanFilter(
        include_sections=frozenset(BundleSection(value) for value in args.include_section),
        exclude_sections=frozenset(BundleSection(value) for value in args.exclude_section),
        extensions=normalize_extensions(args.extensions),
        macho_only=args.macho_only,
    )

    try:
        database = Scanner().scan(
            args.app_bundle,
            cache_dir=args.cache_dir,
            use_cache=not args.no_cache,
            scan_filter=scan_filter,
        )
        report_paths = list(write_scanner_reports(database, args.output_dir / "scanner2"))
        if args.macho_dependencies:
            from tools.bundle_analyzer.macho import (
                MachOAnalyzer,
                build_dependency_graph,
                write_macho_reports,
            )

            binaries = MachOAnalyzer().analyze(database)
            graph = build_dependency_graph(binaries, bundle_root=database.root)
            report_paths.extend(write_macho_reports(binaries, graph, args.output_dir / "macho"))
    except (OSError, ValueError) as exc:
        LOGGER.error("Scan fehlgeschlagen: %s", exc)
        return 2

    statistics = database.statistics
    LOGGER.info("Build %s – Scanner 2.0 abgeschlossen.", BUILD_VERSION)
    LOGGER.info("Dateien: %s", statistics.file_count)
    LOGGER.info(
        "Cache: %s Treffer, %s neu",
        statistics.cache_hits,
        statistics.cache_misses,
    )
    for report_path in report_paths:
        LOGGER.info("Bericht: %s", report_path)
    LOGGER.info("Das App-Bundle wurde nicht verändert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
