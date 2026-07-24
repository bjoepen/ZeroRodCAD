# ZeroRodCAD Desktop

> **Engineering the Perfect String Path**

**ZeroRodCAD Desktop** is an open-source engineering project for designing parametric zero-fret and string-guide systems for Cigar Box Guitars and related string instruments.

Instead of modifying CAD models manually, ZeroRodCAD generates the complete geometry from engineering parameters. The application validates the design and exports manufacturing-ready STL and STEP files together with an engineering report.

The long-term vision is a native desktop application that enables makers, luthiers and instrument builders to design custom zero-fret systems without requiring CAD experience.

---

## Why ZeroRodCAD?

Traditional CAD workflows require manual modelling for every design change.

ZeroRodCAD takes a different approach.

The instrument is described by engineering parameters rather than geometry.

Examples include:

- Body dimensions
- Rod diameter
- Groove diameter
- Number of strings
- String gauges
- String spacing
- Entry geometry
- Safety clearances

The software calculates the resulting geometry automatically.

---

## Current Features

- Parametric CadQuery geometry engine
- Variable string count
- Variable string gauges
- Tangential string-channel calculation
- Automatic engineering validation
- Human-readable project files (`.zerorod`)
- STL export
- STEP export
- Markdown engineering reports
- Desktop application (Build 010 Foundation)
- Automated unit tests
- GitHub Actions CI

---

## Planned Features

- Interactive 3D viewport
- Live parameter updates
- Native macOS application
- Preset library
- Multiple zero-fret systems
- Additional instrument types
- Automatic wall-thickness analysis
- Printability checks
- Multi-language interface

---

# Engineering Philosophy

ZeroRodCAD follows five simple principles.

1. **Parametric First**
   
   Geometry is generated from parameters.

2. **Instrument First**
   
   Every design decision must improve the instrument rather than the CAD model.

3. **Prototype Driven**
   
   Physical prototypes are used to validate every important engineering change.

4. **Transparent Engineering**
   
   Every design decision is documented.

5. **Open Source**
   
   Improvements should benefit the entire maker community.

---

# Repository Structure

```text
ZeroRodCAD-Desktop/
│
├── src/
│   ├── zerorodcad/
│   └── zerorodcad_desktop/
│
├── docs/
├── examples/
├── tests/
├── scripts/
├── exports/
└── .github/
```

---

# Quick Start

Clone the repository

```bash
git clone https://github.com/<YOUR_ACCOUNT>/ZeroRodCAD-Desktop.git
cd ZeroRodCAD-Desktop
```

Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev,desktop]"
```

Run the tests

```bash
pytest -v
```

Start the desktop application

```bash
zerorodcad-desktop
```

---

# Roadmap

| Build | Status | Description              |
| ----- | ------ | ------------------------ |
| 010   | ✅      | Desktop Foundation       |
| 011   | ⬜      | Interactive 3D Preview   |
| 012   | ⬜      | Native macOS Application |
| 013   | ⬜      | Preset Library           |
| 014   | ⬜      | Multi-Instrument Support |
| 1.0   | ⬜      | First Stable Release     |

---

# Contributing

Contributions are welcome.

Please read

- CONTRIBUTING.md
- CODE_OF_CONDUCT.md

before opening a Pull Request.

Engineering changes should always include validation information.

---

# License

Released under the MIT License.

---

## Project Status

**Current Build**

> **Build 010 — Desktop Foundation**

The engineering core is under active development.

The long-term objective is to transform instrument design from manual CAD modelling into reproducible engineering.

---

*"ZeroRodCAD transforms instrument design from manual CAD modeling into reproducible engineering."*
