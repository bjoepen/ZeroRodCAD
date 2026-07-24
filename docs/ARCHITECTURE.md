# Architecture

```text
PySide6 desktop UI
        │
        ▼
Project and validation services
        │
        ▼
ZeroRodCAD parameter model
        │
        ▼
CadQuery geometry engine
        │
        ▼
STL / STEP / Markdown report
```

The user interface does not construct geometry directly. It creates a `ZeroRodParameters` object and calls the same validation and export services used by the CLI.

This separation allows future front ends without duplicating engineering logic.
