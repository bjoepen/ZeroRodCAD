"""Parametric instrument geometry independent of the desktop UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import acos, atan2, cos, degrees, hypot, sin
from typing import Any


@dataclass(frozen=True)
class ZeroRodParameters:
    project_name: str = "CBG Open G"
    body_width: float = 38.0
    body_depth: float = 9.0
    fretboard_height: float = 6.90

    rod_diameter: float = 3.00
    groove_diameter: float = 2.94
    rod_center_z_offset: float = -0.75
    groove_front_clearance: float = 0.01

    string_gauges_inch: tuple[float, ...] = field(default_factory=lambda: (0.036, 0.026, 0.017))
    string_spacing: float = 10.0
    string_inlet_y: float = 0.0
    string_inlet_z: float = 2.80

    channel_diameter: float = 1.15
    channel_overrun_at_inlet: float = 0.8
    channel_rod_clearance: float = 0.05
    minimum_wall: float = 1.20

    @property
    def string_count(self) -> int:
        return len(self.string_gauges_inch)

    @property
    def string_positions_x(self) -> tuple[float, ...]:
        count = self.string_count
        if count == 1:
            return (0.0,)
        total = self.string_spacing * (count - 1)
        start = -total / 2.0
        return tuple(start + index * self.string_spacing for index in range(count))

    @property
    def rod_radius(self) -> float:
        return self.rod_diameter / 2.0

    @property
    def groove_radius(self) -> float:
        return self.groove_diameter / 2.0

    @property
    def channel_radius(self) -> float:
        return self.channel_diameter / 2.0

    @property
    def rod_center_y(self) -> float:
        return self.body_depth - self.rod_radius

    @property
    def rod_center_z(self) -> float:
        return self.fretboard_height + self.rod_center_z_offset

    @property
    def rod_top_z(self) -> float:
        return self.rod_center_z + self.rod_radius

    @property
    def groove_center_y(self) -> float:
        return self.rod_center_y + self.groove_front_clearance

    @property
    def tangent_clearance_radius(self) -> float:
        return self.rod_radius + self.channel_radius + self.channel_rod_clearance

    @property
    def tangent_point_yz(self) -> tuple[float, float]:
        py, pz = self.string_inlet_y, self.string_inlet_z
        cy, cz = self.rod_center_y, self.rod_center_z
        radius = self.tangent_clearance_radius

        vy, vz = py - cy, pz - cz
        distance = hypot(vy, vz)
        if distance <= radius:
            raise ValueError("String inlet lies inside the protected rod envelope.")

        base_angle = atan2(vz, vy)
        delta = acos(radius / distance)
        candidates = []
        for sign in (-1.0, 1.0):
            angle = base_angle + sign * delta
            candidates.append((cy + radius * cos(angle), cz + radius * sin(angle)))

        return min(candidates, key=lambda point: point[0])

    @property
    def channel_contact_y(self) -> float:
        return self.tangent_point_yz[0]

    @property
    def channel_contact_z(self) -> float:
        return self.tangent_point_yz[1]

    @property
    def channel_run(self) -> float:
        return self.channel_contact_y - self.string_inlet_y

    @property
    def channel_rise(self) -> float:
        return self.channel_contact_z - self.string_inlet_z

    @property
    def string_entry_angle_deg(self) -> float:
        return degrees(atan2(self.channel_rise, self.channel_run))

    @property
    def string_diameters_mm(self) -> tuple[float, ...]:
        return tuple(gauge * 25.4 for gauge in self.string_gauges_inch)

    @property
    def string_support_heights(self) -> tuple[float, ...]:
        return tuple(self.rod_top_z + diameter / 2.0 for diameter in self.string_diameters_mm)

    @property
    def string_heights_over_fretboard(self) -> tuple[float, ...]:
        return tuple(height - self.fretboard_height for height in self.string_support_heights)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["string_gauges_inch"] = list(self.string_gauges_inch)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZeroRodParameters:
        cleaned = dict(data)
        if "string_gauges_inch" in cleaned:
            cleaned["string_gauges_inch"] = tuple(float(v) for v in cleaned["string_gauges_inch"])
        allowed = set(cls.__dataclass_fields__)
        unknown = set(cleaned) - allowed
        if unknown:
            raise ValueError(f"Unknown project parameters: {', '.join(sorted(unknown))}")
        return cls(**cleaned)


def default_parameters() -> ZeroRodParameters:
    return ZeroRodParameters()
