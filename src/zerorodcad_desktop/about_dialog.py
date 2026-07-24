"""Native About dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from .application_info import APP_BUILD, APP_NAME, APP_VERSION


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(420)

        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f"Version {APP_VERSION} · Build {APP_BUILD}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(
            "Parametric zero-fret and string-guide design for "
            "Cigar Box Guitars and related string instruments."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        notice = QLabel(
            "Generated geometry must be validated in CAD, in the slicer "
            "and with a physical prototype before use."
        )
        notice.setWordWrap(True)
        notice.setAlignment(Qt.AlignmentFlag.AlignCenter)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addSpacing(8)
        layout.addWidget(description)
        layout.addSpacing(12)
        layout.addWidget(notice)
        layout.addSpacing(12)
        layout.addWidget(buttons)
