"""Background preview jobs."""

from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from zerorodcad.parameters import ZeroRodParameters
from zerorodcad.preview import PreviewScene, build_preview_scene


class PreviewSignals(QObject):
    completed = Signal(int, object)
    failed = Signal(int, str)


class PreviewJob(QRunnable):
    def __init__(self, generation: int, parameters: ZeroRodParameters) -> None:
        super().__init__()
        self.generation = generation
        self.parameters = parameters
        self.signals = PreviewSignals()

    @Slot()
    def run(self) -> None:
        try:
            scene: PreviewScene = build_preview_scene(self.parameters)
            self.signals.completed.emit(self.generation, scene)
        except Exception:
            self.signals.failed.emit(self.generation, traceback.format_exc())
