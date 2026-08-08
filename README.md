# ZeroRodCAD

Parametrisches CAD- und Desktop-Projekt für das ZeroRod-System.

ZeroRodCAD erzeugt die Geometrie des ZeroRod-Nullbundsystems, stellt eine Vorschau bereit und exportiert Fertigungsdaten wie STL und STEP. Das Projekt befindet sich aktuell in einer Architektur- und Packaging-Modernisierung mit dem Ziel, die CAD-Engine klar von der Desktop-Oberfläche zu trennen und die macOS-Anwendung deutlich schlanker zu machen.

## Aktueller Stand

Die bisherige PySide6-Desktop-Anwendung ist weiterhin vollständig funktionsfähig und dient als Referenz- und Fallback-Implementierung.

Die wichtigsten aktuellen Ergebnisse:

- Python-Standard: **Python >= 3.13,<3.14**
- CadQuery: **2.8.0**
- OCP: **cadquery-ocp-novtk 7.9.3.1.1**
- VTK ist für die relevanten ZeroRodCAD-Kernworkflows nicht erforderlich.
- Ein kleiner, reproduzierbarer CadQuery-Patch entkoppelt die nicht-VTK-bezogenen Funktionen von den bisherigen eager VTK-Imports.
- Geometry, Tessellation, PreviewMesh, STL und STEP funktionieren ohne VTK.
- Das reale macOS-App-Bundle konnte von **910.51 MiB auf 380.12 MiB** reduziert werden.
- Reale Reduktion: **530.39 MiB / 58.25 %**
- Statische VTK-Dateien im No-VTK-Bundle: **0**
- Runtime-Trace-VTK-Treffer: **0**
- OS-Level-VTK-Mappings: **0**
- Ein Real-World-Test der No-VTK-App bestätigte die vollständige Funktionalität.

## Architektur-Evaluation

### TE-001 – No-VTK Feasibility

Ergebnis: **FAIL für unverändertes CadQuery 2.8.0**

Grund: CadQuery importiert `vtkmodules` bereits beim Modulimport, obwohl die eigentlichen ZeroRodCAD-Kernfunktionen VTK nicht benötigen.

### TE-001.1 – CadQuery No-VTK Import Decoupling

Ergebnis: **PASS**

Ein kleiner, lokaler Patch verschiebt VTK-/IVtk-Imports in die Funktionen, die VTK tatsächlich benötigen.

Dadurch funktionieren ohne VTK:

- CAD-Geometrie
- `Shape.tessellate()`
- PreviewMesh
- STL
- STEP

VTK-spezifische Funktionen schlagen ohne VTK kontrolliert mit verständlichen `ImportError`-Meldungen fehl.

### TE-001.2 – No-VTK Production Bundle Proof

Ergebnis: **Gate C PASS / Evidence Confidence HIGH**

Gemessene Werte:

| Kennzahl    | VTK-Baseline | No-VTK     |
| ----------- | ------------ | ---------- |
| App-Größe   | 910.51 MiB   | 380.12 MiB |
| VTK         | 584.10 MiB   | 0          |
| OCP         | 217.50 MiB   | 216.03 MiB |
| Dateianzahl | 1349         | 713        |

Die App startet, Geometry/Preview/STL/STEP funktionieren und VTK ist weder statisch noch zur Laufzeit vorhanden.

### TE-002 – Tauri v2 + Three.js Preview Architecture

Ergebnis: **Gate D PASS / Evidence Confidence MEDIUM**

Erfolgreich nachgewiesene Kette:

```text
Tauri v2
    ↓
Rust / Tauri Command Layer
    ↓
Python 3.13 Sidecar
    ↓
ZeroRodCAD Engine
    ↓
CadQuery + No-VTK OCP
    ↓
PreviewMesh
    ↓
zerorod-mesh/v1 JSON
    ↓
Three.js BufferGeometry
```

Wesentliche Messwerte:

- Modellbau + Tessellation: ca. **0.149 s**
- Mesh-Serialisierung: ca. **0.0003 s**
- Mesh-Payload: **60,079 Byte**
- Three.js Geometry-Erzeugung: ca. **0.157 ms**
- aktueller Onefile-Sidecar-Roundtrip: ca. **15 s**

Die 15 Sekunden entstehen durch PyInstaller-Onefile-Self-Extraction, nicht durch CAD-Engine, JSON oder Three.js.

## Aktuelle Technology Evaluation

### TE-002.1 – Sidecar Runtime Strategy & Human Validation

TE-002.1 untersucht die produktiv geeignete Sidecar-Strategie.

Verglichen werden:

1. PyInstaller onefile / One-Shot
2. PyInstaller onedir / One-Shot
3. persistenter Sidecar
4. optional: persistent + onedir

Bewertet werden unter anderem:

- Cold Start
- Warm Request Latency
- Speicherverhalten
- Prozess-Cleanup
- Crash Recovery
- Disk Footprint
- VTK-/PySide6-Freiheit
- Wartbarkeit
- reale Benutzerinteraktion

TE-002.1 endet mit:

- **Gate E-A** – Engineering Gate
- **Gate E-B** – Human Validation Gate

Erst bei `E-A PASS` und `E-B PASS` wird Gate E insgesamt als bestanden betrachtet.

## Zielarchitektur

Die derzeit bevorzugte, noch nicht final verabschiedete Zielarchitektur lautet:

```text
ZeroRodCAD Desktop
│
├── Tauri v2
│   ├── native Desktop Shell
│   ├── UI
│   └── Three.js Preview
│
├── Rust Process / IPC Layer
│
└── Python Engine Sidecar
    ├── ZeroRodCAD Engine
    ├── CadQuery
    ├── cadquery-ocp-novtk
    ├── Geometry
    ├── Tessellation
    ├── STL
    └── STEP
```

Die bestehende PySide6-App bleibt bis zu einer späteren, ausdrücklich beschlossenen Migration als funktionierende Referenz und Rollback-Pfad erhalten.

## Entwicklung

### Entwicklungsumgebung

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

### Tests

```bash
python -m pytest
```

### Qualität

```bash
python -m ruff check .
python -m ruff format --check .
```

### Bestehende Build-/Analysewerkzeuge

Das Repository enthält inzwischen umfangreiche Werkzeuge für:

- Bundle Scanner 2.0
- Dependency- und Mach-O-Analyse
- Dead-Library-Analyse
- Bundle Health / Risk Score
- Report Engine
- Analysis Pipeline
- Runtime Trace
- No-VTK Technology Evaluations
- Tauri-/Sidecar-PoCs

Diese Werkzeuge sind ein fester Bestandteil der technischen Entscheidungsfindung und werden für reproduzierbare Architektur- und Packaging-Nachweise verwendet.

## Repository-Grundsätze

- Python 3.13 ist verbindlicher Standard.
- Neue Dependencies werden vor Aufnahme auf Pflegezustand, Lizenz, Plattformunterstützung und tatsächliche Notwendigkeit geprüft.
- Technology Evaluations bleiben im bestehenden Repository; neue Ideen erzeugen nicht automatisch neue Repositories.
- Produktive Architekturänderungen werden erst nach reproduzierbarer Evidenz und klar definierten Gates beschlossen.
- Bestehende funktionsfähige Referenzpfade werden erst entfernt, wenn eine neue Architektur vollständig validiert wurde.

## Dokumentation

Wichtige technische Dokumentation befindet sich unter:

```text
docs/
docs/research/
```

Die aktuellen Technology Evaluations liegen unter anderem in:

```text
docs/research/TE-001-No-VTK/
docs/research/TE-001.1-CadQuery-NoVTK/
docs/research/TE-001.2-NoVTK-Bundle/
docs/research/TE-002-Tauri-ThreeJS/
docs/research/TE-002.1-Sidecar-Runtime/
```

## Status

ZeroRodCAD befindet sich derzeit zwischen erfolgreicher Architektur-Evaluation und möglicher produktiver Desktop-Migration.

Die technische Frage, ob Tauri v2 + Three.js + Python Sidecar + No-VTK CadQuery/OCP grundsätzlich funktioniert, wurde positiv beantwortet.

Offen ist nun die produktiv optimale Sidecar-Runtime-Strategie und die abschließende menschliche Interaktionsvalidierung.
