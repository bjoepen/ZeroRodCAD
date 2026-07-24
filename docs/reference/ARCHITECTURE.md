# Architecture

```text
PySide6 desktop workspace
        │
        ├── live parameter editor
        ├── rendered report
        └── interactive preview
                 │
                 ▼
        background scene builder
                 │
                 ▼
CadQuery geometry and tessellation
        │
        ├── manufacturing export
        └── plain preview scene data
```

## Separation of responsibilities

### Engine

The `zerorodcad` package owns:

- parameters,
- geometry,
- validation,
- project files,
- reports,
- STL and STEP export.

### Desktop

The `zerorodcad_desktop` package owns:

- widgets,
- user interaction,
- background preview jobs,
- visualization,
- file dialogs.

### Preview scene

The engine converts CadQuery solids into plain Python structures:

- vertices,
- triangle indices,
- line segments,
- layer names.

The preview widget never modifies engineering geometry.
