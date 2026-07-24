"""Application entry point."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from .application_info import (
    APP_NAME,
    APP_VERSION,
    ORGANIZATION_DOMAIN,
    ORGANIZATION_NAME,
)
from .diagnostics import diagnostics_as_text
from .main_window import MainWindow


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Print runtime diagnostics and exit.",
    )
    return parser.parse_args(arguments)


def configure_application_metadata() -> None:
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANIZATION_DOMAIN)


def main() -> None:
    args = parse_arguments(sys.argv[1:])
    if args.diagnose:
        print(diagnostics_as_text())
        return

    configure_application_metadata()
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
