"""CadQuery model generation."""

from __future__ import annotations

import cadquery as cq

from .geometry import cylinder_between, fuse_all
from .parameters import ZeroRodParameters


def build_base_body(p: ZeroRodParameters) -> cq.Workplane:
    shoulder_z = p.fretboard_height - 1.35
    profile = (
        cq.Workplane("YZ")
        .moveTo(0.0, 0.0)
        .lineTo(p.body_depth, 0.0)
        .lineTo(p.body_depth, shoulder_z)
        .threePointArc(
            (p.body_depth / 2.0, p.fretboard_height),
            (0.0, shoulder_z),
        )
        .close()
    )
    return profile.extrude(p.body_width / 2.0, both=True)


def build_groove_cutter(p: ZeroRodParameters) -> cq.Workplane:
    start = (-p.body_width / 2.0 - 1.0, p.groove_center_y, p.rod_center_z)
    end = (p.body_width / 2.0 + 1.0, p.groove_center_y, p.rod_center_z)
    return cylinder_between(start, end, p.groove_radius)


def string_channel_cutter(p: ZeroRodParameters, x: float) -> cq.Workplane:
    start_y, start_z = p.string_inlet_y, p.string_inlet_z
    end_y, end_z = p.channel_contact_y, p.channel_contact_z

    dy, dz = end_y - start_y, end_z - start_z
    length = (dy * dy + dz * dz) ** 0.5
    if length <= 0:
        raise ValueError("Invalid channel path.")

    uy, uz = dy / length, dz / length
    start = (
        x,
        start_y - uy * p.channel_overrun_at_inlet,
        start_z - uz * p.channel_overrun_at_inlet,
    )
    end = (x, end_y, end_z)
    return cylinder_between(start, end, p.channel_radius)


def build_channel_cutters(p: ZeroRodParameters) -> cq.Workplane:
    return fuse_all([string_channel_cutter(p, x) for x in p.string_positions_x])


def build_body(p: ZeroRodParameters) -> cq.Workplane:
    body = build_base_body(p)
    body = body.cut(build_groove_cutter(p))
    body = body.cut(build_channel_cutters(p))
    return body.clean()


def build_rod(p: ZeroRodParameters) -> cq.Workplane:
    start = (-p.body_width / 2.0, p.rod_center_y, p.rod_center_z)
    end = (p.body_width / 2.0, p.rod_center_y, p.rod_center_z)
    return cylinder_between(start, end, p.rod_radius)


def build_assembly(p: ZeroRodParameters) -> cq.Assembly:
    assembly = cq.Assembly(name="ZeroRodCAD")
    assembly.add(build_body(p), name="body", color=cq.Color(0.72, 0.72, 0.72))
    assembly.add(build_rod(p), name="rod", color=cq.Color(0.35, 0.35, 0.38))
    return assembly
