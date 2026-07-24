"""Background workers for expensive preview generation."""

from __future__ import annotations

import traceback
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from zerorodcad.parameters import ZeroRodParameters


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
            # CadQuery/OCP is intentionally loaded inside the worker only.
            from zerorodcad.preview import build_preview_scene

            scene: Any = build_preview_scene(self.parameters)
            self.signals.completed.emit(self.generation, scene)
        except Exception:
            self.signals.failed.emit(self.generation, traceback.format_exc())
