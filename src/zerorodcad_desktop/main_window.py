"""Build 011 interactive design workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QSignalBlocker, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from zerorodcad.export import export_project
from zerorodcad.parameters import ZeroRodParameters
from zerorodcad.project import load_project, save_project
from zerorodcad.report import build_report
from zerorodcad.validation import ValidationResult, validate_parameters

from .about_dialog import AboutDialog
from .application_info import APP_NAME
from .diagnostics_dialog import DiagnosticsDialog
from .preview_widget import PreviewWidget
from .workers import PreviewJob


class MainWindow(QMainWindow):
    PREVIEW_DELAY_MS = 280

    def __init__(self) -> None:
        super().__init__()
        self.current_path: Path | None = None
        self.settings = QSettings()
        self.setAcceptDrops(True)
        self._generation = 0
        self._thread_pool = QThreadPool.globalInstance()

        self.setWindowTitle("ZeroRodCAD Desktop 0.11.2")
        self.resize(1240, 780)

        self._build_actions()
        self._build_ui()
        self._build_menu_and_toolbar()
        self._connect_live_updates()

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._start_preview_build)

        self._load_parameters(ZeroRodParameters())
        self._update_workspace()

    def _build_actions(self) -> None:
        self.new_action = QAction("New", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.new_project)

        self.open_action = QAction("Open…", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_project)

        self.save_action = QAction("Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_current_project)

        self.save_as_action = QAction("Save As…", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.save_project_as)

        self.export_action = QAction("Export STL / STEP…", self)
        self.export_action.triggered.connect(self.export_files)

        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)

        self.about_action = QAction(f"About {APP_NAME}", self)
        self.about_action.triggered.connect(self.show_about_dialog)

        self.diagnostics_action = QAction("Diagnostics…", self)
        self.diagnostics_action.triggered.connect(self.show_diagnostics_dialog)

        self.documentation_action = QAction("Open Documentation", self)
        self.documentation_action.triggered.connect(self.open_local_documentation)

    def _build_ui(self) -> None:
        splitter = QSplitter()
        splitter.addWidget(self._build_parameter_sidebar())
        splitter.addWidget(self._build_workspace())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 860])
        self.setCentralWidget(splitter)

    def _build_parameter_sidebar(self) -> QWidget:
        self.project_name = QLineEdit()

        self.body_width = self._double(38.0, 10.0, 200.0)
        self.body_depth = self._double(9.0, 5.0, 30.0)
        self.fretboard_height = self._double(6.90, 1.0, 30.0, decimals=2)

        self.rod_diameter = self._double(3.0, 0.5, 10.0)
        self.groove_diameter = self._double(2.94, 0.3, 10.0, decimals=2)
        self.channel_clearance = self._double(0.05, 0.0, 2.0, decimals=2)

        self.string_count = QSpinBox()
        self.string_count.setRange(1, 12)
        self.string_count.valueChanged.connect(self._sync_gauge_fields)
        self.gauges = QLineEdit()
        self.gauges.setPlaceholderText("0.036, 0.026, 0.017")
        self.string_spacing = self._double(10.0, 1.0, 30.0)
        self.string_inlet_z = self._double(2.8, 0.0, 20.0)
        self.channel_diameter = self._double(1.15, 0.2, 5.0)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel("<h2>ZeroRod parameters</h2>"))

        project_group = QGroupBox("Project")
        project_form = QFormLayout(project_group)
        project_form.addRow("Name", self.project_name)
        layout.addWidget(project_group)

        body_group = QGroupBox("Body and reference")
        body_form = QFormLayout(body_group)
        body_form.addRow("Width [mm]", self.body_width)
        body_form.addRow("Depth [mm]", self.body_depth)
        body_form.addRow("Fretboard height [mm]", self.fretboard_height)
        layout.addWidget(body_group)

        rod_group = QGroupBox("Rod and groove")
        rod_form = QFormLayout(rod_group)
        rod_form.addRow("Rod diameter [mm]", self.rod_diameter)
        rod_form.addRow("Groove diameter [mm]", self.groove_diameter)
        rod_form.addRow("Rod clearance [mm]", self.channel_clearance)
        layout.addWidget(rod_group)

        strings_group = QGroupBox("Strings and channels")
        strings_form = QFormLayout(strings_group)
        strings_form.addRow("String count", self.string_count)
        strings_form.addRow("Gauges [inch]", self.gauges)
        strings_form.addRow("Spacing [mm]", self.string_spacing)
        strings_form.addRow("Inlet Z [mm]", self.string_inlet_z)
        strings_form.addRow("Channel Ø [mm]", self.channel_diameter)
        layout.addWidget(strings_group)

        export_button = QPushButton("Export STL / STEP")
        export_button.clicked.connect(self.export_files)
        layout.addWidget(export_button)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setMinimumWidth(350)
        return scroll

    def _build_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QVBoxLayout(workspace)

        self.status_banner = QLabel()
        self.status_banner.setMinimumHeight(42)
        self.status_banner.setContentsMargins(14, 8, 14, 8)
        layout.addWidget(self.status_banner)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_preview_tab(), "3D Preview")

        self.report = QTextBrowser()
        self.report.setOpenExternalLinks(False)
        self.tabs.addTab(self.report, "Instrument Report")
        layout.addWidget(self.tabs)

        return workspace

    def _build_preview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        controls = QHBoxLayout()
        self.body_toggle = QCheckBox("Body")
        self.body_toggle.setChecked(True)
        self.rod_toggle = QCheckBox("Rod")
        self.rod_toggle.setChecked(True)
        self.strings_toggle = QCheckBox("Strings")
        self.strings_toggle.setChecked(True)
        reset_button = QPushButton("Reset View")

        controls.addWidget(self.body_toggle)
        controls.addWidget(self.rod_toggle)
        controls.addWidget(self.strings_toggle)
        controls.addStretch()

        self.preview = PreviewWidget()
        reset_button.clicked.connect(self.preview.reset_view)
        controls.addWidget(reset_button)

        self.body_toggle.toggled.connect(
            lambda value: self.preview.set_layer_visibility(body=value)
        )
        self.rod_toggle.toggled.connect(lambda value: self.preview.set_layer_visibility(rod=value))
        self.strings_toggle.toggled.connect(
            lambda value: self.preview.set_layer_visibility(strings=value)
        )

        layout.addLayout(controls)
        layout.addWidget(self.preview)
        return widget

    def _build_menu_and_toolbar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        for action in (
            self.new_action,
            self.open_action,
            self.save_action,
            self.save_as_action,
            self.export_action,
            self.quit_action,
        ):
            file_menu.addAction(action)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.documentation_action)
        help_menu.addAction(self.diagnostics_action)
        help_menu.addSeparator()
        help_menu.addAction(self.about_action)

        toolbar = QToolBar("Project")
        toolbar.setMovable(False)
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.export_action)
        self.addToolBar(toolbar)

    def _connect_live_updates(self) -> None:
        self.project_name.textChanged.connect(self._schedule_update)
        self.gauges.textChanged.connect(self._schedule_update)

        for widget in (
            self.body_width,
            self.body_depth,
            self.fretboard_height,
            self.rod_diameter,
            self.groove_diameter,
            self.string_count,
            self.string_spacing,
            self.string_inlet_z,
            self.channel_diameter,
            self.channel_clearance,
        ):
            widget.valueChanged.connect(self._schedule_update)

    def _schedule_update(self, *args) -> None:
        self._update_report_only()
        self._preview_timer.start(self.PREVIEW_DELAY_MS)

    def _update_workspace(self) -> None:
        self._update_report_only()
        self._preview_timer.start(0)

    def _update_report_only(self) -> None:
        try:
            parameters = self._parameters()
            validation = validate_parameters(parameters)
            self.report.setMarkdown(build_report(parameters))
            self._show_validation_status(validation)
            if not validation.is_valid:
                self.preview.clear_scene("Correct the validation errors to rebuild the preview.")
        except Exception as exc:
            self.report.setHtml(f"<h2>Input error</h2><p>{self._escape(str(exc))}</p>")
            self._show_input_error(str(exc))
            self.preview.clear_scene("Correct the input values to rebuild the preview.")

    def _start_preview_build(self) -> None:
        try:
            parameters = self._parameters()
            validation = validate_parameters(parameters)
            if not validation.is_valid:
                return
        except Exception:
            return

        self._generation += 1
        generation = self._generation
        self.statusBar().showMessage("Building preview…")

        job = PreviewJob(generation, parameters)
        job.signals.completed.connect(self._preview_completed)
        job.signals.failed.connect(self._preview_failed)
        self._thread_pool.start(job)

    def _preview_completed(self, generation: int, scene: object) -> None:
        if generation != self._generation:
            return
        self.preview.set_scene(scene)
        self.statusBar().showMessage("Preview up to date")

    def _preview_failed(self, generation: int, traceback_text: str) -> None:
        if generation != self._generation:
            return
        self.preview.set_error("Preview generation failed.\n\n" + traceback_text)
        self.statusBar().showMessage("Preview generation failed")

    def _show_validation_status(self, validation: ValidationResult) -> None:
        if validation.errors:
            text = "● Invalid design — " + validation.errors[0]
            background = "#fce8e6"
            foreground = "#9c1c13"
        elif validation.warnings:
            text = "● Valid with warning — " + validation.warnings[0]
            background = "#fff4ce"
            foreground = "#725200"
        else:
            text = "● Valid design — all parameter checks passed"
            background = "#e6f4ea"
            foreground = "#176b35"

        self.status_banner.setText(text)
        self.status_banner.setStyleSheet(
            f"background:{background}; color:{foreground};border-radius:6px; font-weight:600;"
        )

    def _show_input_error(self, message: str) -> None:
        self.status_banner.setText("● Input error — " + message)
        self.status_banner.setStyleSheet(
            "background:#fce8e6; color:#9c1c13;border-radius:6px; font-weight:600;"
        )

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
        with QSignalBlocker(self.gauges):
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
        widgets = (
            self.project_name,
            self.body_width,
            self.body_depth,
            self.fretboard_height,
            self.rod_diameter,
            self.groove_diameter,
            self.string_count,
            self.gauges,
            self.string_spacing,
            self.string_inlet_z,
            self.channel_diameter,
            self.channel_clearance,
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
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
        del blockers

    def new_project(self) -> None:
        self.current_path = None
        self._load_parameters(ZeroRodParameters())
        self._update_workspace()

    def open_project(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open ZeroRodCAD project",
            self._dialog_directory(),
            "ZeroRodCAD Project (*.zerorod)",
        )
        if not filename:
            return
        self._open_project_path(Path(filename))

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
            str(
                Path(self._dialog_directory())
                / f"{self.project_name.text().strip() or 'project'}.zerorod"
            ),
            "ZeroRodCAD Project (*.zerorod)",
        )
        if not filename:
            return
        try:
            self.current_path = save_project(filename, self._parameters())
            self._remember_directory(self.current_path.parent)
            self.statusBar().showMessage(f"Saved {self.current_path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def export_files(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select export directory",
            self._dialog_directory(),
        )
        if not directory:
            return
        try:
            self._remember_directory(Path(directory))
            created = export_project(directory, self._parameters())
            QMessageBox.information(
                self,
                "Export complete",
                "\n".join(str(path) for path in created),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def show_about_dialog(self) -> None:
        AboutDialog(self).exec()

    def show_diagnostics_dialog(self) -> None:
        DiagnosticsDialog(self).exec()

    def open_local_documentation(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        documentation = repository_root / "docs" / "INSTALL_MACOS.md"
        if documentation.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(documentation)))
            return
        QMessageBox.information(
            self,
            "Documentation",
            "The source documentation is not included at this application location.",
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if any(Path(url.toLocalFile()).suffix.lower() == ".zerorod" for url in urls):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() != ".zerorod":
                continue
            self._open_project_path(path)
            event.acceptProposedAction()
            return

    def _open_project_path(self, path: Path) -> None:
        try:
            parameters = load_project(path)
            self.current_path = path
            self._remember_directory(path.parent)
            self._load_parameters(parameters)
            self._update_workspace()
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))

    def _dialog_directory(self) -> str:
        return self.settings.value("paths/last_directory", str(Path.home()), type=str)

    def _remember_directory(self, directory: Path) -> None:
        self.settings.setValue("paths/last_directory", str(directory))

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
