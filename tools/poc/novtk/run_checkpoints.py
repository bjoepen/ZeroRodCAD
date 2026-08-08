"""TE-001 Gate A checkpoint runner.

Runs the real ZeroRodCAD engine (no dummy geometry) through the checkpoint
sequence from the TE-001 mandate: import, geometry, tessellate, preview-mesh,
stl, step. Must be executed with the ``.venv-novtk-poc`` interpreter. Writes a
deterministic JSON report and the raw Build 021 M1 recorder trace.

Usage: python tools/poc/novtk/run_checkpoints.py --report PATH --raw-trace PATH
"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
import traceback
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.poc.novtk import runtime_trace_adapter  # noqa: E402
from tools.poc.novtk.vtk_import_blocker import install as install_blocker  # noqa: E402
from tools.poc.novtk.vtk_import_blocker import uninstall as uninstall_blocker  # noqa: E402

CHECKPOINTS = ("import", "geometry", "tessellate", "preview-mesh", "stl", "step")


@dataclass
class CheckpointResult:
    name: str
    status: str  # "pass" | "fail" | "skipped"
    detail: str = ""
    sys_modules_vtk_hits: list[str] = field(default_factory=list)


def _scan_sys_modules_for_vtk() -> list[str]:
    return sorted(
        name for name in sys.modules if name.split(".", 1)[0].lower() in {"vtk", "vtkmodules"}
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def run_checkpoints() -> list[CheckpointResult]:
    results: list[CheckpointResult] = []
    blocker = install_blocker()

    # --- import ---------------------------------------------------------
    try:
        import cadquery  # noqa: F401

        results.append(CheckpointResult("import", "pass", "", _scan_sys_modules_for_vtk()))
    except Exception as exc:  # broad: any import-time failure is evidence, not a bug
        blocked = (
            f" (blocked names so far: {blocker.blocked_names})" if blocker.blocked_names else ""
        )
        tb = traceback.format_exc()
        # Keep only File/import-statement lines so the failing cadquery source
        # location (the actual root cause) survives in the report, not just the message.
        relevant = "\n".join(
            line.strip()
            for line in tb.splitlines()
            if line.strip().startswith("File ") or "import" in line
        )
        results.append(
            CheckpointResult(
                "import",
                "fail",
                f"{type(exc).__name__}: {exc}{blocked}\n{relevant}",
                _scan_sys_modules_for_vtk(),
            )
        )
        for remaining in CHECKPOINTS[1:]:
            results.append(
                CheckpointResult(remaining, "skipped", "blocked by failed import checkpoint")
            )
        uninstall_blocker(blocker)
        return results

    # From here on real ZeroRodCAD engine modules are used, per section 9-16.
    from zerorodcad.export import export_project
    from zerorodcad.model import build_assembly
    from zerorodcad.parameters import default_parameters
    from zerorodcad.preview import build_preview_scene, tessellate_workplane

    parameters = default_parameters()

    # --- geometry --------------------------------------------------------
    assembly = None
    try:
        assembly = build_assembly(parameters)
        objects = list(assembly.objects.values())
        if not objects:
            raise ValueError("assembly contains no objects")
        bbox = objects[0].shapes[0].BoundingBox() if objects[0].shapes else None
        if bbox is None:
            raise ValueError("first assembly object has no shape/bounding box")
        detail = f"objects={len(objects)} bbox=({bbox.xlen:.2f},{bbox.ylen:.2f},{bbox.zlen:.2f})"
        results.append(CheckpointResult("geometry", "pass", detail, _scan_sys_modules_for_vtk()))
    except Exception as exc:
        results.append(
            CheckpointResult(
                "geometry", "fail", f"{type(exc).__name__}: {exc}", _scan_sys_modules_for_vtk()
            )
        )
        for remaining in CHECKPOINTS[2:]:
            results.append(
                CheckpointResult(remaining, "skipped", "blocked by failed geometry checkpoint")
            )
        uninstall_blocker(blocker)
        return results

    # --- tessellate --------------------------------------------------------
    body_mesh = None
    try:
        from zerorodcad.model import build_body

        body_mesh = tessellate_workplane("body", build_body(parameters))
        if len(body_mesh.vertices) == 0 or len(body_mesh.triangles) == 0:
            raise ValueError("tessellation produced no vertices/triangles")
        for vertex in body_mesh.vertices:
            for coordinate in vertex:
                if math.isnan(coordinate) or math.isinf(coordinate):
                    raise ValueError(f"non-finite vertex coordinate: {vertex}")
        max_index = len(body_mesh.vertices) - 1
        for triangle in body_mesh.triangles:
            if any(index < 0 or index > max_index for index in triangle):
                raise ValueError(f"triangle index out of range: {triangle}")
        detail = f"vertices={len(body_mesh.vertices)} triangles={len(body_mesh.triangles)}"
        results.append(CheckpointResult("tessellate", "pass", detail, _scan_sys_modules_for_vtk()))
    except Exception as exc:
        results.append(
            CheckpointResult(
                "tessellate", "fail", f"{type(exc).__name__}: {exc}", _scan_sys_modules_for_vtk()
            )
        )
        for remaining in CHECKPOINTS[3:]:
            results.append(
                CheckpointResult(remaining, "skipped", "blocked by failed tessellate checkpoint")
            )
        uninstall_blocker(blocker)
        return results

    # --- preview-mesh --------------------------------------------------------
    try:
        scene = build_preview_scene(parameters)
        if not scene.meshes:
            raise ValueError("preview scene has no meshes")
        for mesh in scene.meshes:
            if len(mesh.vertices) == 0 or len(mesh.triangles) == 0:
                raise ValueError(f"mesh '{mesh.name}' has no vertices/triangles")
        detail = f"meshes={[m.name for m in scene.meshes]} lines={list(scene.lines)}"
        results.append(
            CheckpointResult("preview-mesh", "pass", detail, _scan_sys_modules_for_vtk())
        )
    except Exception as exc:
        results.append(
            CheckpointResult(
                "preview-mesh", "fail", f"{type(exc).__name__}: {exc}", _scan_sys_modules_for_vtk()
            )
        )
        for remaining in CHECKPOINTS[4:]:
            results.append(
                CheckpointResult(remaining, "skipped", "blocked by failed preview-mesh checkpoint")
            )
        uninstall_blocker(blocker)
        return results

    # --- stl + step (single real export_project call produces both) --------
    try:
        with tempfile.TemporaryDirectory(prefix="te001-export-") as export_dir:
            body_path, assembly_path, _report_path = export_project(export_dir, parameters)
            stl_ok = body_path.is_file() and body_path.stat().st_size > 0
            step_ok = assembly_path.is_file() and assembly_path.stat().st_size > 0
            stl_size = body_path.stat().st_size if body_path.is_file() else 0
            step_size = assembly_path.stat().st_size if assembly_path.is_file() else 0
            modules_hits = _scan_sys_modules_for_vtk()
            if stl_ok:
                results.append(CheckpointResult("stl", "pass", f"size={stl_size}B", modules_hits))
            else:
                results.append(
                    CheckpointResult("stl", "fail", "STL file missing or empty", modules_hits)
                )
            if step_ok:
                results.append(CheckpointResult("step", "pass", f"size={step_size}B", modules_hits))
            else:
                results.append(
                    CheckpointResult("step", "fail", "STEP file missing or empty", modules_hits)
                )
    except Exception as exc:
        modules_hits = _scan_sys_modules_for_vtk()
        results.append(
            CheckpointResult("stl", "fail", f"{type(exc).__name__}: {exc}", modules_hits)
        )
        results.append(
            CheckpointResult("step", "skipped", "blocked by failed stl/step export", modules_hits)
        )

    uninstall_blocker(blocker)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TE-001 Gate A checkpoint runner")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--raw-trace", type=Path, required=True)
    args = parser.parse_args(argv)

    started_at = _utc_now()
    runtime_trace_adapter.enable_recording(args.raw_trace)

    results = run_checkpoints()

    report = {
        "schema": "zerorodcad/te001-novtk-checkpoints/v1",
        "started_at": started_at,
        "ended_at": _utc_now(),
        "python_version": sys.version.split()[0],
        "checkpoints": [asdict(result) for result in results],
        "overall": "pass" if all(r.status == "pass" for r in results) else "fail",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    import json

    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Checkpoint report written to: {args.report}")
    return 0 if report["overall"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
