"""Lightweight interactive 3D preview using QPainter."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import cos, radians, sin

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPolygonF, QWheelEvent
from PySide6.QtWidgets import QWidget

from zerorodcad.preview_data import Line3D, Point3D, PreviewMesh, PreviewScene


@dataclass(frozen=True)
class ProjectedTriangle:
    depth: float
    points: tuple[QPointF, QPointF, QPointF]
    shade: float


class PreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(420, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._scene: PreviewScene | None = None
        self._error: str | None = None
        self._yaw = -28.0
        self._pitch = 22.0
        self._zoom = 1.0
        self._last_mouse = None

        self.show_body = True
        self.show_rod = True
        self.show_strings = True

    def set_scene(self, scene: PreviewScene) -> None:
        self._scene = scene
        self._error = None
        self.update()

    def set_error(self, message: str) -> None:
        self._scene = None
        self._error = message
        self.update()

    def clear_scene(self, message: str = "Preview unavailable") -> None:
        self._scene = None
        self._error = message
        self.update()

    def reset_view(self) -> None:
        self._yaw = -28.0
        self._pitch = 22.0
        self._zoom = 1.0
        self.update()

    def set_layer_visibility(
        self,
        *,
        body: bool | None = None,
        rod: bool | None = None,
        strings: bool | None = None,
    ) -> None:
        if body is not None:
            self.show_body = body
        if rod is not None:
            self.show_rod = rod
        if strings is not None:
            self.show_strings = strings
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_mouse = event.position()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last_mouse is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        delta = event.position() - self._last_mouse
        self._last_mouse = event.position()
        self._yaw += delta.x() * 0.65
        self._pitch = max(-89.0, min(89.0, self._pitch + delta.y() * 0.65))
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._last_mouse = None
        event.accept()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        self._zoom = max(0.25, min(6.0, self._zoom * factor))
        self.update()
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f5f6f7"))

        if self._scene is None:
            painter.setPen(QColor("#555555"))
            text = self._error or "Building preview…"
            painter.drawText(
                self.rect().adjusted(24, 24, -24, -24),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                text,
            )
            return

        all_points = [vertex for mesh in self._visible_meshes() for vertex in mesh.vertices]
        for line in self._visible_lines():
            all_points.extend(line)

        if not all_points:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No visible layers")
            return

        rotated = [self._rotate(point) for point in all_points]
        min_x = min(point[0] for point in rotated)
        max_x = max(point[0] for point in rotated)
        min_z = min(point[2] for point in rotated)
        max_z = max(point[2] for point in rotated)

        span_x = max(max_x - min_x, 1e-6)
        span_z = max(max_z - min_z, 1e-6)
        margin = 36.0
        base_scale = min(
            max(1.0, (self.width() - 2 * margin) / span_x),
            max(1.0, (self.height() - 2 * margin) / span_z),
        )
        scale = base_scale * self._zoom
        center_x = (min_x + max_x) / 2.0
        center_z = (min_z + max_z) / 2.0

        def project(point: Point3D) -> QPointF:
            rx, _, rz = self._rotate(point)
            return QPointF(
                self.width() / 2.0 + (rx - center_x) * scale,
                self.height() / 2.0 - (rz - center_z) * scale,
            )

        triangles: list[tuple[ProjectedTriangle, str]] = []
        for mesh in self._visible_meshes():
            for a, b, c in mesh.triangles:
                pa3 = self._rotate(mesh.vertices[a])
                pb3 = self._rotate(mesh.vertices[b])
                pc3 = self._rotate(mesh.vertices[c])
                depth = (pa3[1] + pb3[1] + pc3[1]) / 3.0
                shade = self._triangle_shade(pa3, pb3, pc3)
                triangles.append(
                    (
                        ProjectedTriangle(
                            depth=depth,
                            points=(
                                project(mesh.vertices[a]),
                                project(mesh.vertices[b]),
                                project(mesh.vertices[c]),
                            ),
                            shade=shade,
                        ),
                        mesh.name,
                    )
                )

        triangles.sort(key=lambda item: item[0].depth, reverse=True)
        painter.setPen(QPen(QColor(0, 0, 0, 35), 0.45))

        for triangle, layer in triangles:
            base = QColor("#b7bcc2") if layer == "body" else QColor("#565b61")
            light = max(0.48, min(1.0, triangle.shade))
            color = QColor(
                int(base.red() * light),
                int(base.green() * light),
                int(base.blue() * light),
                235,
            )
            painter.setBrush(color)
            painter.drawPolygon(QPolygonF(triangle.points))

        if self.show_strings:
            painter.setPen(QPen(QColor("#b0702d"), 2.0))
            for start, end in self._scene.lines.get("strings", ()):
                painter.drawLine(project(start), project(end))

        painter.setPen(QColor("#666666"))
        painter.drawText(
            12,
            self.height() - 12,
            "Drag: rotate   •   Wheel: zoom",
        )

    def _visible_meshes(self) -> Iterable[PreviewMesh]:
        if self._scene is None:
            return ()
        return (
            mesh
            for mesh in self._scene.meshes
            if (mesh.name == "body" and self.show_body) or (mesh.name == "rod" and self.show_rod)
        )

    def _visible_lines(self) -> Iterable[Line3D]:
        if self._scene is None or not self.show_strings:
            return ()
        return self._scene.lines.get("strings", ())

    def _rotate(self, point: Point3D) -> Point3D:
        x, y, z = point
        yaw = radians(self._yaw)
        pitch = radians(self._pitch)

        x1 = x * cos(yaw) - y * sin(yaw)
        y1 = x * sin(yaw) + y * cos(yaw)
        z1 = z

        y2 = y1 * cos(pitch) - z1 * sin(pitch)
        z2 = y1 * sin(pitch) + z1 * cos(pitch)
        return (x1, y2, z2)

    @staticmethod
    def _triangle_shade(a: Point3D, b: Point3D, c: Point3D) -> float:
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = max((nx * nx + ny * ny + nz * nz) ** 0.5, 1e-9)
        nx, ny, nz = nx / length, ny / length, nz / length
        light = (0.3, -0.6, 0.74)
        diffuse = abs(nx * light[0] + ny * light[1] + nz * light[2])
        return 0.58 + diffuse * 0.42
