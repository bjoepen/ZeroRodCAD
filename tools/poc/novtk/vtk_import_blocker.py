"""Active import blocker for TE-001. Not used outside this evaluation.

Installed on ``sys.meta_path`` before the first ``cadquery`` import so that any
attempt to import ``vtk``/``vtkmodules`` is caught deterministically and logged,
rather than surfacing as an ordinary ``ModuleNotFoundError`` from the default
path finder.
"""

from __future__ import annotations

import importlib.abc
import sys
from dataclasses import dataclass, field


@dataclass
class VTKImportBlocker(importlib.abc.MetaPathFinder):
    """Blocks ``vtk`` and ``vtkmodules`` imports; records every blocked name."""

    blocked_names: list[str] = field(default_factory=list)

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".", 1)[0].lower()
        if root in {"vtk", "vtkmodules"}:
            self.blocked_names.append(fullname)
            raise ImportError(f"VTK import blocked during TE-001: {fullname}")
        return None


def install() -> VTKImportBlocker:
    """Install the blocker at the front of ``sys.meta_path`` and return it."""
    blocker = VTKImportBlocker()
    sys.meta_path.insert(0, blocker)
    return blocker


def uninstall(blocker: VTKImportBlocker) -> None:
    """Remove the blocker from ``sys.meta_path``, restoring normal import behavior."""
    if blocker in sys.meta_path:
        sys.meta_path.remove(blocker)
