"""Runtime diagnostics for local installations and packaged applications."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path


@dataclass(frozen=True)
class DiagnosticItem:
    name: str
    value: str
    ok: bool = True


def _distribution_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not installed"


def collect_diagnostics() -> tuple[DiagnosticItem, ...]:
    executable = Path(sys.executable)
    items = [
        DiagnosticItem("Platform", platform.platform()),
        DiagnosticItem("Machine", platform.machine()),
        DiagnosticItem("Python", platform.python_version()),
        DiagnosticItem("Executable", str(executable)),
        DiagnosticItem("Frozen application", "yes" if getattr(sys, "frozen", False) else "no"),
        DiagnosticItem("CadQuery", _distribution_version("cadquery")),
        DiagnosticItem("PySide6", _distribution_version("PySide6")),
        DiagnosticItem(
            "Writable home directory",
            str(Path.home()),
            Path.home().exists() and os_access_writable(Path.home()),
        ),
    ]
    return tuple(items)


def os_access_writable(path: Path) -> bool:
    try:
        probe = path / ".zerorodcad-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def diagnostics_as_text() -> str:
    lines = ["ZeroRodCAD Desktop Diagnostics", ""]
    for item in collect_diagnostics():
        status = "OK" if item.ok else "ERROR"
        lines.append(f"[{status}] {item.name}: {item.value}")
    return "\n".join(lines)
