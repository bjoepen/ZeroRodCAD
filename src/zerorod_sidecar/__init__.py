"""ZeroRodCAD Desktop 2.0 — productive Python sidecar (Build 022 M2).

Speaks zerorod-sidecar/v1 over stdin/stdout to the Rust process/IPC layer
(desktop/src-tauri). Uses only zerorodcad.parameters / zerorodcad.preview /
zerorodcad.preview_data — the CAD engine itself is untouched by the
migration (ADR-022-001). No PySide6, no VTK, no Qt.

Carries the architecture principles proven in
docs/research/TE-002-Tauri-ThreeJS/, docs/research/TE-002.1-Sidecar-Runtime/
and docs/research/TE-002.2B-Tauri-Bundle-Optimization/ into the productive
path — it is a controlled adoption, not a copy of
tools/poc/tauri/sidecar/, which stays untouched as the research reference.
"""
