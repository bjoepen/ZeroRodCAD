#!/usr/bin/env python3
"""Compatibility entry point for the Build 021 runtime trace controller."""

from __future__ import annotations

import sys

try:
    from .trace_runtime import main
except ImportError:
    from trace_runtime import main


if __name__ == "__main__":
    print(
        "trace_runtime_imports.py is deprecated; use tools/trace_runtime.py.",
        file=sys.stderr,
    )
    raise SystemExit(main())
