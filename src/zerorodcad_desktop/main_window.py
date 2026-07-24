"""Build 010 desktop window without the Build 011 3D viewport."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from zerorodcad.export import export_project
from zerorodcad.parameters import ZeroRodParameters
from zerorodcad.project import load_project, save_project
from zerorodcad.report import build_report
from zerorodcad.validation import validate_parameters


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.current_path: Path | None = None
        self.setWindowTitle("ZeroRodCAD Desktop 0.10")
        self.resize(980, 680)
        self._build_ui()
        self._build_menu()
        self._load_parameters(ZeroRodParameters())
        self.recalculate()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)

        form_widget = QWidget()
        form = QFormLayout(form_widget)

        self.project_name = QLineEdit()
        self.body_width = self._double(38.0, 10.0, 200.0)
        self.body_depth = self._double(9.0, 5.0, 30.0)
        self.fretboard_height = self._double(6.90, 1.0, 30.0, decimals=2)
        self.rod_diameter = self._double(3.0, 0.5, 10.0)
        self.groove_diameter = self._double(2.94, 0.3, 10.0, decimals=2)
        self.string_count = QSpinBox()
        self.string_count.setRange(1, 12)
        self.string_count.valueChanged.connect(self._sync_gauge_fields)
        self.string_spacing = self._double(10.0, 1.0, 30.0)
        self.string_inlet_z = self._double(2.8, 0.0, 20.0)
        self.channel_diameter = self._double(1.15, 0.2, 5.0)
        self.channel_clearance = self._double(0.05, 0.0, 2.0, decimals=2)
        self.gauges = QLineEdit()
        self.gauges.setPlaceholderText("0.036, 0.026, 0.017")

        form.addRow("Project name", self.project_name)
        form.addRow("Body width [mm]", self.body_width)
        form.addRow("Body depth [mm]", self.body_depth)
        form.addRow("Fretboard height [mm]", self.fretboard_height)
        form.addRow("Rod diameter [mm]", self.rod_diameter)
        form.addRow("Groove diameter [mm]", self.groove_diameter)
        form.addRow("String count", self.string_count)
        form.addRow("String gauges [inch]", self.gauges)
        form.addRow("String spacing [mm]", self.string_spacing)
        form.addRow("String inlet Z [mm]", self.string_inlet_z)
        form.addRow("Channel diameter [mm]", self.channel_diameter)
        form.addRow("Rod clearance [mm]", self.channel_clearance)

        buttons = QHBoxLayout()
        recalc = QPushButton("Calculate model")
        recalc.clicked.connect(self.recalculate)
        export = QPushButton("Export STL / STEP")
        export.clicked.connect(self.export_files)
        buttons.addWidget(recalc)
        buttons.addWidget(export)

        left = QVBoxLayout()
        left.addWidget(QLabel("<h2>ZeroRod parameters</h2>"))
        left.addWidget(form_widget)
        left.addLayout(buttons)
        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        right = QVBoxLayout()
        right.addWidget(QLabel("<h2>Calculation and validation</h2>"))
        right.addWidget(self.results)
        right_widget = QWidget()
        right_widget.setLayout(right)

        root.addWidget(left_widget, 1)
        root.addWidget(right_widget, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Build 010 – desktop foundation")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)

        open_action = QAction("Open…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_current_project)

        save_as_action = QAction("Save As…", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)

        export_action = QAction("Export STL / STEP…", self)
        export_action.triggered.connect(self.export_files)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        for action in (
            new_action,
            open_action,
            save_action,
            save_as_action,
            export_action,
            quit_action,
        ):
            file_menu.addAction(action)

    @staticmethod
    def _double(
        value: float,
        minimum: float,
        maximum: float,
        *,
        decimals: int = 3,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setDecimals(decimals)
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        widget.setSingleStep(0.1)
        return widget

    def _sync_gauge_fields(self) -> None:
        values = self._parse_gauges(allow_mismatch=True)
        count = self.string_count.value()
        if len(values) < count:
            values.extend([0.020] * (count - len(values)))
        else:
            values = values[:count]
        self.gauges.setText(", ".join(f"{value:.3f}" for value in values))

    def _parse_gauges(self, *, allow_mismatch: bool = False) -> list[float]:
        try:
            values = [
                float(item.strip())
                for item in self.gauges.text().replace(";", ",").split(",")
                if item.strip()
            ]
        except ValueError as exc:
            raise ValueError("String gauges must be comma-separated numbers.") from exc

        if not allow_mismatch and len(values) != self.string_count.value():
            raise ValueError("Number of gauges must match the selected string count.")
        return values

    def _parameters(self) -> ZeroRodParameters:
        return ZeroRodParameters(
            project_name=self.project_name.text().strip() or "Untitled ZeroRod",
            body_width=self.body_width.value(),
            body_depth=self.body_depth.value(),
            fretboard_height=self.fretboard_height.value(),
            rod_diameter=self.rod_diameter.value(),
            groove_diameter=self.groove_diameter.value(),
            string_gauges_inch=tuple(self._parse_gauges()),
            string_spacing=self.string_spacing.value(),
            string_inlet_z=self.string_inlet_z.value(),
            channel_diameter=self.channel_diameter.value(),
            channel_rod_clearance=self.channel_clearance.value(),
        )

    def _load_parameters(self, p: ZeroRodParameters) -> None:
        self.project_name.setText(p.project_name)
        self.body_width.setValue(p.body_width)
        self.body_depth.setValue(p.body_depth)
        self.fretboard_height.setValue(p.fretboard_height)
        self.rod_diameter.setValue(p.rod_diameter)
        self.groove_diameter.setValue(p.groove_diameter)
        self.string_count.setValue(p.string_count)
        self.gauges.setText(", ".join(f"{gauge:.3f}" for gauge in p.string_gauges_inch))
        self.string_spacing.setValue(p.string_spacing)
        self.string_inlet_z.setValue(p.string_inlet_z)
        self.channel_diameter.setValue(p.channel_diameter)
        self.channel_clearance.setValue(p.channel_rod_clearance)

    def recalculate(self) -> None:
        try:
            parameters = self._parameters()
            validation = validate_parameters(parameters)
            report = build_report(parameters)
            self.results.setPlainText(report)
            if validation.is_valid:
                self.statusBar().showMessage("Parameters calculated successfully")
            else:
                self.statusBar().showMessage("Validation errors found")
        except Exception as exc:
            self.results.setPlainText(f"ERROR\n\n{exc}")
            self.statusBar().showMessage("Input error")

    def new_project(self) -> None:
        self.current_path = None
        self._load_parameters(ZeroRodParameters())
        self.recalculate()

    def open_project(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open ZeroRodCAD project",
            "",
            "ZeroRodCAD Project (*.zerorod)",
        )
        if not filename:
            return
        try:
            parameters = load_project(filename)
            self.current_path = Path(filename)
            self._load_parameters(parameters)
            self.recalculate()
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))

    def save_current_project(self) -> None:
        if self.current_path is None:
            self.save_project_as()
            return
        try:
            save_project(self.current_path, self._parameters())
            self.statusBar().showMessage(f"Saved {self.current_path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def save_project_as(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save ZeroRodCAD project",
            f"{self.project_name.text().strip() or 'project'}.zerorod",
            "ZeroRodCAD Project (*.zerorod)",
        )
        if not filename:
            return
        try:
            self.current_path = save_project(filename, self._parameters())
            self.statusBar().showMessage(f"Saved {self.current_path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def export_files(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select export directory")
        if not directory:
            return
        try:
            created = export_project(directory, self._parameters())
            QMessageBox.information(
                self,
                "Export complete",
                "\n".join(str(path) for path in created),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
