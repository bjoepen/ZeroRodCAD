"""Command-line export tool."""

from __future__ import annotations

import argparse
from pathlib import Path

from .export import export_project
from .project import load_project


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a ZeroRodCAD project.")
    parser.add_argument("project", type=Path, help="Path to a .zerorod project file")
    parser.add_argument("-o", "--output", type=Path, default=Path("exports"))
    args = parser.parse_args()

    parameters = load_project(args.project)
    paths = export_project(args.output, parameters)
    for path in paths:
        print(path)
