# TE-002 — Mesh Contract (`zerorod-mesh/v1`)

## Shape

```json
{
  "schema": "zerorod-mesh/v1",
  "meshes": [
    { "name": "body", "positions": [x, y, z, x, y, z, ...], "indices": [0, 1, 2, ...] },
    { "name": "rod",  "positions": [...], "indices": [...] }
  ],
  "lines": [
    { "name": "strings", "positions": [x, y, z, x, y, z, ...] }
  ],
  "bounds": { "min": [x, y, z], "max": [x, y, z] },
  "timing": { "model_and_tessellation_seconds": 0.149, "serialization_seconds": 0.0003 }
}
```

Flat float/int arrays throughout, per section 12 — no base64, no binary packing for this PoC
(see `Performance.md`/`Conclusion.md` question 8 for whether that remains true at production
scale).

- `meshes[].positions` — flat `[x,y,z,x,y,z,...]`, length always a multiple of 3.
- `meshes[].indices` — flat triangle indices `[a,b,c,a,b,c,...]`, length always a multiple of 3,
  every value `>= 0` and `< positions.length/3`.
- `lines[].positions` — flat `[x,y,z,x,y,z,...]`; consecutive pairs of points are one segment
  (matches `PreviewScene.lines`'s `Line3D = tuple[Point3D, Point3D]` shape one-to-one).
- `bounds` — computed over **every** mesh vertex and **every** line endpoint (not mesh vertices
  alone), so a camera fit to `bounds` shows the complete model including the virtual string
  overlays, matching section 20's "Initialansicht muss das gesamte Modell sichtbar machen."
- `timing` — sidecar-internal measurements, not part of the core mesh data; used for
  `Performance.md`.

## Source mapping (`tools/poc/tauri/sidecar/mesh_contract.py::scene_to_mesh_contract`)

Directly converts `zerorodcad.preview_data.PreviewScene`:

| `PreviewScene` | `zerorod-mesh/v1` |
|---|---|
| `mesh.vertices: tuple[Point3D, ...]` | `meshes[].positions` (flattened) |
| `mesh.triangles: tuple[Triangle, ...]` | `meshes[].indices` (flattened) |
| `lines[name]: tuple[Line3D, ...]` | one `lines[]` entry per dict key, positions flattened |
| *(computed)* | `bounds` |

No colors/materials/metadata are carried in v1 — the existing PySide6 preview widget's own color
choices (`preview_widget.py`) were not part of this contract; TE-002's Three.js side uses one
flat `MeshStandardMaterial` for all meshes (section 19's "MeshStandardMaterial oder ähnlich
einfacher Standard-Materialpfad").

## Real measured output (default ZeroRod parameters, section 24-25)

| | body | rod | strings (lines) |
|---|---:|---:|---:|
| vertices / points | 720 | 146 | 12 |
| triangles | 710 | 140 | — |

`bounds`: `min = [-19.0, -4.0, 0.0]`, `max = [19.0, 14.0, 8.1072]`.

Total serialized JSON response: **60,079 bytes** (~59 KiB) — see `Performance.md` for the full
payload/timing breakdown.

## Frontend conversion (`experiments/te002-tauri/frontend/src/mesh.js`)

```js
geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
geometry.setIndex(new THREE.BufferAttribute(indexArrayFor(vertexCount, indices), 1)); // Uint16 or Uint32
geometry.computeVertexNormals();
```

`indexArrayFor()` picks `Uint16Array` below 65,536 vertices and `Uint32Array` above — both meshes
in the real default model (720 and 146 vertices) use `Uint16Array`; tested directly for both
branches (`test_mesh_contract.py`/`mesh.test.js`).
