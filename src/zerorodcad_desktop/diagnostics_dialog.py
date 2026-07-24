"""Diagnostics dialog used for installation and packaged-app support."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .diagnostics import diagnostics_as_text


class DiagnosticsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ZeroRodCAD Diagnostics")
        self.resize(720, 420)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText(diagnostics_as_text())

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_to_clipboard)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.addButton(copy_button, QDialogButtonBox.ButtonRole.ActionRole)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        layout.addWidget(buttons)

    def copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self.text.toPlainText())
        QMessageBox.information(self, "Diagnostics", "Diagnostics copied to the clipboard.")
