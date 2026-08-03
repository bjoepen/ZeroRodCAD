#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repository_root = Path(__file__).resolve().parents[1]
    root_text = str(repository_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

from zerorod_analysis.benchmark import benchmark_bundle, benchmark_payload  # noqa: E402
from zerorod_analysis.build_metadata import benchmark_version  # noqa: E402
from zerorod_analysis.exceptions import AnalysisError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark the ZeroRodCAD analysis pipeline")
    parser.add_argument("app_bundle", type=Path, nargs="?")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--version", action="version", version=benchmark_version())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.app_bundle is None:
        build_parser().error("the following arguments are required: app_bundle")
    try:
        result = benchmark_bundle(
            args.app_bundle,
            iterations=args.iterations,
            warmup=args.warmup,
            use_cache=not args.no_cache,
        )
    except (AnalysisError, OSError, ValueError) as exc:
        print(f"Benchmark fehlgeschlagen: {exc}", file=sys.stderr)
        return 2

    payload = benchmark_payload(result)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
