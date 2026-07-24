"""Application entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from .application_info import (
    APP_NAME,
    APP_VERSION,
    ORGANIZATION_DOMAIN,
    ORGANIZATION_NAME,
)
from .diagnostics import diagnostics_as_text
from .main_window import MainWindow
from .startup import configure_logging, install_exception_hook


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Print runtime diagnostics and exit.",
    )
    parser.add_argument(
        "--startup-test",
        action="store_true",
        help="Create the application and main window, then exit.",
    )
    return parser.parse_args(arguments)


def configure_application_metadata() -> None:
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANIZATION_DOMAIN)


def main() -> None:
    log_path = configure_logging()
    install_exception_hook()
    args = parse_arguments(sys.argv[1:])

    if args.diagnose:
        print(diagnostics_as_text())
        print(f"Log: {log_path}")
        return

    configure_application_metadata()
    QApplication.setAttribute(
        Qt.ApplicationAttribute.AA_DontShowIconsInMenus,
        False,
    )

    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        if args.startup_test:
            print("STARTUP_OK")
            print(f"Log: {log_path}")
            window.close()
            return
        window.show()
        raise SystemExit(app.exec())
    except Exception as exc:
        logging.getLogger(__name__).exception("Fatal startup error")
        _show_startup_error(exc, log_path)
        raise


def _show_startup_error(exc: Exception, log_path: Path) -> None:
    try:
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None,
            f"{APP_NAME} could not start",
            f"{exc}\n\nDiagnostic log:\n{log_path}",
        )
        app.processEvents()
    except Exception:
        print(
            f"{APP_NAME} could not start: {exc}\nDiagnostic log: {log_path}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
