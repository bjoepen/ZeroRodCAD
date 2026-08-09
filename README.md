# ZeroRodCAD

Parametrisches CAD- und Desktop-Projekt für das ZeroRod-System.

ZeroRodCAD erzeugt die Geometrie des ZeroRod-Nullbundsystems, stellt eine Vorschau bereit und exportiert Fertigungsdaten wie STL und STEP. Die Technology-Evaluation-Phase zur zukünftigen Desktop-Architektur ist abgeschlossen; die Zielarchitektur (Tauri v2 + Rust Process/IPC-Schicht + persistenter Python-Sidecar + Three.js) ist vom Projektverantwortlichen genehmigt. Die produktive Migration ist vorbereitet, aber noch nicht gestartet.

## Aktueller Stand

```text
Technology Evaluation:  COMPLETE
Architecture:           ACCEPTED
Productive migration:   NEXT (Build 022 – noch nicht gestartet)
```

Die bisherige PySide6-Desktop-Anwendung ist weiterhin vollständig funktionsfähig und dient als aktuelle Referenz-, Feature-Parity- und Fallback-Implementierung, bis die Tauri-Migration vollständig validiert und eine ausdrückliche Entscheidung zur Ablösung getroffen ist. Sie wird durch diesen Auftrag nicht verändert oder entfernt.

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

### TE-002.1 – Sidecar Runtime Strategy & Human Validation

Ergebnis: **Gate E-A PASS** (Engineering)

Verglichen wurden vier Sidecar-Strategien (onefile/onedir × one-shot/persistent). Empfohlene und
angenommene Variante: **persistent + onedir** — Cold Start ca. **0.644 s** statt ca. 15–17 s bei
onefile, kein struktureller Orphan-Process-Risiko bei erzwungenem Kill (im Gegensatz zu onefile).

### TE-002.2A – Tauri Bundle Composition Discovery

Ergebnis: **Gate F-A PASS**

Das ungeoptimierte Tauri-PoC-Bundle (706.051.017 Byte / 673.34 MiB / 372 Dateien) besteht zu
**98.15 %** (660.93 MiB) aus Sidecar-Payload; die Tauri-/Rust-/Frontend-Schicht selbst ist nur
13.04 MiB groß. Fünf Optimierungskandidaten wurden identifiziert (u. a. doppeltes
Onefile-Fallback, doppelte OpenCASCADE-Dylibs, numba/llvmlite, scipy) — noch ohne Änderung.

### TE-002.2B – Targeted Bundle Optimization

Ergebnis: **Gate F-B PASS**

Alle fünf Kandidaten wurden einzeln untersucht, root-caused und als sicher entfernbar bestätigt.
Finales optimiertes Bundle:

```text
293.892.882 Byte / ~280.27 MiB / 193 Dateien
```

Gesamtersparnis gegenüber der TE-002.1-Baseline (673.34 MiB): **393.07 MiB / 58.37 %**.

Keine Performance-Regression (Cold Start ~0.612 s, Warm Median ~0.121 s), keine Memory-Regression,
VTK = 0, PySide6/Qt = 0. Vollständige funktionale Validierung (Launch, Preview, STL, STEP,
wiederholte Requests, Fehlerbehandlung, Shutdown, 0 Orphan-Prozesse).

**Human Validation (Projektverantwortlicher, 2026-08-09): PASS within implemented PoC scope.** App
startet real, ZeroRod-Modell und seine vorhandenen Bestandteile (Body, Rod, Virtual Strings) werden
korrekt dargestellt, Rotation und Zoom funktionieren. Parameteränderungen sind in der
PoC-Oberfläche noch **nicht implementiert** (NOT IMPLEMENTED / NOT TESTABLE) — das ist eine
Scope-Lücke, kein Fehler. Details:
`docs/research/TE-002.2B-Tauri-Bundle-Optimization/HUMAN-VALIDATION.md`.

## Technology Evaluation Phase: COMPLETE

TE-001 bis TE-002.2B sind vollständig abgeschlossen. Es ist keine TE-002.3 geplant — weitere offene
Produktfragen (vollständige Parameter-UI, Export-UI, Feature-Parität) gehören in die Migration
(Build 023 ff.), nicht in eine weitere Grundlagen-Evaluation.

## Architektur-Entscheidung (ACCEPTED)

Die Zielarchitektur ist final entschieden und im ADR dokumentiert:
[`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md)
(Status: Accepted, 2026-08-09).

```text
ZeroRodCAD Desktop 2.0
│
├── Tauri v2
│   ├── native Desktop Shell
│   ├── WebView UI
│   └── Three.js 3D Preview
│
├── Rust Process / IPC Layer
│
└── Persistenter Python 3.13 Sidecar (PyInstaller onedir)
    ├── ZeroRodCAD Engine (unverändert)
    ├── CadQuery
    ├── cadquery-ocp-novtk
    ├── Geometry
    ├── Tessellation / PreviewMesh
    ├── STL
    └── STEP
```

**No-VTK**, **No-PySide6** sind Ziel der produktiven Architektur. Die bestehende PySide6-App bleibt
bis zu einer späteren, ausdrücklich beschlossenen Retirement-Entscheidung (frühestens nach Build
026) als funktionierende Referenz, Feature-Parity-Baseline und Rollback-Pfad erhalten — sie wird
durch die Architekturentscheidung nicht verändert oder entfernt.

Migrationsplan und Build-022-Vorbereitung: [`docs/migration/README.md`](docs/migration/README.md),
[`docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md`](docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md).

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

Die abgeschlossenen Technology Evaluations liegen unter:

```text
docs/research/TE-001-No-VTK/
docs/research/TE-001.1-CadQuery-NoVTK/
docs/research/TE-001.2-NoVTK-Bundle/
docs/research/TE-002-Tauri-ThreeJS/
docs/research/TE-002.1-Sidecar-Runtime/
docs/research/TE-002.2A-Tauri-Bundle-Discovery/
docs/research/TE-002.2B-Tauri-Bundle-Optimization/
```

Der finale ADR sowie die Migrationsplanung liegen unter:

```text
docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md
docs/migration/README.md
docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md
```

## Status

```text
Technology Evaluation:  COMPLETE
Architecture:           ACCEPTED
Productive migration:   NEXT
```

Die technische Frage, ob Tauri v2 + Three.js + Python Sidecar + No-VTK CadQuery/OCP grundsätzlich funktioniert, wurde positiv beantwortet — inklusive produktiv geeigneter Sidecar-Runtime-Strategie (persistent + onedir), optimierter Bundle-Größe (~280.27 MiB) und realer menschlicher Interaktionsvalidierung des finalen PoC (PASS within implemented PoC scope, Parameteränderungen ausdrücklich noch nicht implementiert).

Die produktive Migration ist geplant, aber noch **nicht gestartet**. Nächster Schritt: Build 022 – Tauri Desktop Foundation (`docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md`).
