"""Immutable renderer registry."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ReportRenderer
from .models import ReportFormat


@dataclass(frozen=True, slots=True)
class RendererRegistry:
    renderers: tuple[ReportRenderer, ...]

    def __post_init__(self) -> None:
        names = [renderer.name for renderer in self.renderers]
        formats = [renderer.format for renderer in self.renderers]
        if len(names) != len(set(names)):
            raise ValueError("renderer names must be unique")
        if len(formats) != len(set(formats)):
            raise ValueError("renderer formats must be unique")

    def select(self, formats: frozenset[ReportFormat]) -> tuple[ReportRenderer, ...]:
        return tuple(renderer for renderer in self.renderers if renderer.format in formats)
