# Build 011 – Interactive Design Workspace

## Objective

Transform Build 010 from a parameter form with a text report into an interactive instrument-design workspace.

## Scope

- interactive model preview,
- rotate and zoom,
- visibility controls,
- live parameter processing,
- rendered report,
- asynchronous model generation,
- documentation and regression tests.

## Architecture decision

The preview deliberately avoids an additional VTK/PyVista dependency.

CadQuery produces tessellated model data. A custom PySide6 widget projects the triangles into the window and draws them using `QPainter`.

Benefits:

- uses the existing PySide6 installation,
- avoids a large additional runtime,
- keeps the repository understandable,
- supports macOS, Linux and Windows in principle,
- separates preview geometry from manufacturing export.

Trade-off:

The preview is an inspection aid, not a replacement for a professional STEP viewer.

## User interaction

| Action | Result |
|---|---|
| Change parameter | Immediate validation/report update |
| Pause after change | Background preview rebuild |
| Drag preview | Rotate |
| Mouse wheel | Zoom |
| Reset View | Restore camera |
| Toggle Body | Show/hide body |
| Toggle Rod | Show/hide reference rod |
| Toggle Strings | Show/hide virtual strings |

## Definition of Done

- [x] Preview receives plain tessellated scene data.
- [x] GUI stays responsive during geometry construction.
- [x] Old background results cannot overwrite newer input.
- [x] Invalid parameters do not trigger geometry export.
- [x] Report is rendered instead of displayed as Markdown source.
- [x] Existing project and export functions remain available.
- [x] Build documentation and upgrade instructions are present.
- [ ] Local macOS GUI execution confirmed by repository owner.
- [ ] STL and STEP inspected after Build 011.
- [ ] Physical prototype produced from Build 011.
