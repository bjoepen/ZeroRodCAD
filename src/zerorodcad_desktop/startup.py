"""Startup logging and fatal-error handling."""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path


def log_directory() -> Path:
    if sys.platform == "darwin":
        directory = Path.home() / "Library" / "Logs" / "ZeroRodCAD"
    else:
        directory = Path.home() / ".zerorodcad" / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def configure_logging() -> Path:
    path = log_directory() / "zerorodcad.log"
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    logging.getLogger(__name__).info("Application startup")
    return path


def install_exception_hook() -> None:
    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.getLogger(__name__).critical("Unhandled exception\n%s", message)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception
