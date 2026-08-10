# ZeroRodCAD

Parametrisches CAD- und Desktop-Projekt für das ZeroRod-System.

ZeroRodCAD erzeugt die Geometrie des ZeroRod-Nullbundsystems, stellt eine Vorschau bereit und exportiert Fertigungsdaten wie STL und STEP. Die produktive Desktop-2.0-Architektur ist **Tauri v2** (WebView-UI, Three.js-3D-Vorschau, Rust-Prozess-/IPC-Schicht, persistenter Python-3.13-Sidecar, CadQuery/cadquery-ocp-novtk) — evidenzbasiert entschieden ([ADR-022-001](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md), Status: Accepted), mit **Build 022** produktiv etabliert (alle fünf Meilensteine, Gate PASS inklusive menschlicher Validierung, wo vorgesehen) und mit **Build 023** um eine produktive, parametergetriebene Live-Vorschau erweitert: ein Parameter-Panel treibt die echte Engine, Änderungen werden nach kurzer Debounce-Verzögerung automatisch neu gerendert — ebenfalls alle fünf Meilensteine abgeschlossen, Gate PASS inklusive menschlicher Validierung.

**Wichtig:** Build 022 und Build 023 etablieren zusammen die produktive Desktop-2.0-**Foundation** samt parametergetriebener Live-Vorschau — es handelt sich weiterhin nicht um eine vollständige Migration. Export-UI (STL/STEP) und volle Feature-Parität mit der bestehenden PySide6-Anwendung folgen in späteren Builds (024–026).

## Aktueller Stand

```text
Technology Evaluation:     COMPLETE
Architecture:              ACCEPTED
Build 022:                 COMPLETE
Desktop 2.0 Foundation:    ESTABLISHED
Build 023:                 COMPLETE (M1-M5 COMPLETE — Gate BUILD-023: PASS)
Parameters & Live Preview: ESTABLISHED
Next:                      Build 024 — STL / STEP Export Workflow
```

Die bisherige PySide6-Desktop-Anwendung ist weiterhin vollständig funktionsfähig und dient als aktuelle Referenz-, Feature-Parity- und Fallback-Implementierung, bis die Tauri-Migration vollständig validiert und eine ausdrückliche Entscheidung zur Ablösung getroffen ist. Sie wurde durch Build 022 und Build 023 nicht verändert oder entfernt.

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

**No-VTK**, **No-PySide6** sind erreicht in der produktiven Tauri-Laufzeit (final gemessen: 0 VTK-,
0 PySide6/Qt-Dateien im Release-Bundle). Die bestehende PySide6-App bleibt bis zu einer späteren,
ausdrücklich beschlossenen Retirement-Entscheidung (frühestens nach Build 026) als funktionierende
Referenz, Feature-Parity-Baseline und Rollback-Pfad erhalten — sie wurde durch Build 022 nicht
verändert oder entfernt.

Mit Build 022 ist die produktive Desktop-2.0-**Foundation** etabliert — Tauri v2 + Rust-Prozessschicht
+ persistenter Python-Sidecar + Three.js-Vorschau funktionieren als reales, getestetes, verpacktes
Produkt (Release-Bundle: 285.21 MiB). Das bedeutet **nicht**, dass die Migration der bestehenden
PySide6-Funktionalität abgeschlossen ist — Parameter-Editing, Export-UI und volle Feature-Parität
sind explizit Aufgabe der folgenden Builds (023–026).

Migrationsplan und Build-Dokumentation: [`docs/migration/README.md`](docs/migration/README.md),
[`docs/migration/BUILD-022-COMPLETION.md`](docs/migration/BUILD-022-COMPLETION.md).

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
docs/migration/BUILD-022-M1-TAURI-FOUNDATION.md
docs/migration/BUILD-022-M2-SIDECAR-LIFECYCLE.md
docs/migration/BUILD-022-M2-HUMAN-VALIDATION.md
docs/migration/BUILD-022-M3-THREEJS-PREVIEW.md
docs/migration/BUILD-022-M3-HUMAN-VALIDATION.md
docs/migration/BUILD-022-M4-PRODUCTIVE-PACKAGING.md
docs/migration/BUILD-022-M4-HUMAN-VALIDATION.md
docs/migration/BUILD-022-COMPLETION.md
docs/migration/BUILD-023-HANDOFF.md
docs/migration/BUILD-023-M1-PARAMETER-DISCOVERY.md
docs/migration/BUILD-023-M1-PARAMETER-CONTRACT.md
docs/contracts/ZEROROD-PARAMETERS-V1.md
```

## Status

```text
Technology Evaluation:     COMPLETE
Architecture:              ACCEPTED
Build 022:                 COMPLETE
Desktop 2.0 Foundation:    ESTABLISHED
  M1 — Tauri Desktop Foundation:       COMPLETE
  M2 — Productive Sidecar & Lifecycle: COMPLETE
  M3 — Three.js Preview Foundation:    COMPLETE
  M4 — Productive Packaging Baseline:  COMPLETE
  M5 — Integration & Build Completion: COMPLETE
Build 023 — Parameters & Live Preview: COMPLETE
  M1 — Parameter Model & Request Contract Foundation: COMPLETE — Gate PASS
  M2 — Parameter Controls Foundation:                 COMPLETE — Gate PASS, Human PASS
  M3 — Parameter-to-Engine Integration:                COMPLETE — Gate PASS, Human PASS
  M4 — Live Preview Behavior & UX:                     COMPLETE — Gate PASS, Human PASS
  M5 — Integration & Build Completion:                 COMPLETE — Gate PASS
Parameters & Live Preview: ESTABLISHED
Next:                       Build 024 — STL / STEP Export Workflow
```

Die technische Frage, ob Tauri v2 + Three.js + Python Sidecar + No-VTK CadQuery/OCP grundsätzlich funktioniert, wurde positiv beantwortet — inklusive produktiv geeigneter Sidecar-Runtime-Strategie (persistent + onedir), optimierter Bundle-Größe und realer menschlicher Interaktionsvalidierung.

Build 022 ist vollständig abgeschlossen: Milestone 1 (produktive Tauri-v2-Projektstruktur, funktionierende WebView↔Rust-IPC-Bridge), Milestone 2 (persistenter Python-Sidecar, Rust Engine Manager mit Lazy Start/Timeout/Crash-Detection/Restart/Shutdown), Milestone 3 (Three.js Preview Foundation: echtes ZeroRod-Mesh wird über Three.js gerendert, OrbitControls, Kamera-Fit, Resize, Refresh ohne Restgeometrie), Milestone 4 (Productive Packaging Baseline: produktives hash-gated Dylib-Dedup, reproduzierbare Build-Pipeline, Release-Build 285.21 MiB — 1.76 % über der TE-002.2B-Referenz von 280.27 MiB, vollständig erklärt) und Milestone 5 (Integration & Build Completion: Gesamtsystem-Audit, Architektur-Konformitätsprüfung gegen ADR-022-001, finales Master-Validierungsgate) sind abgeschlossen, alle mit Gate PASS. Details: [`docs/migration/BUILD-022-COMPLETION.md`](docs/migration/BUILD-022-COMPLETION.md).

Build 023 ist ebenfalls vollständig abgeschlossen: Milestone 1 (kanonischer `zerorod-parameters/v1`-Request-Contract, 16 Felder, End-to-End gegen den echten Sidecar bewiesen), Milestone 2 (produktives Parameter-Panel mit allen 16 Feldern, canonical Defaults, lokalem Draft-/Dirty-State, lokaler Validierung), Milestone 3 (Apply verbindet den Parameter-Draft mit der echten Engine — reale Geometrieänderung im Three.js-Viewport bewiesen), Milestone 4 (automatische, debounced Live-Vorschau mit generation-basiertem Stale-Response-Schutz, Request-Coalescing und kamera-schonendem Refit-Verhalten) und Milestone 5 (Gesamtsystem-Audit, Architektur-Konformitätsprüfung, finales Master-Validierungsgate) sind abgeschlossen, alle mit Gate PASS und — wo vorgesehen — menschlicher Validierung PASS durch den Project Owner. Details: [`docs/migration/BUILD-023-COMPLETION.md`](docs/migration/BUILD-023-COMPLETION.md).

**Desktop 2.0 Foundation: ESTABLISHED. Parameters & Live Preview: ESTABLISHED.** Das bedeutet, dass die neue Architektur real, getestet und produktiv gebaut funktioniert und dass Parameter-Editing samt echter, engine-getriebener Live-Regenerierung jetzt ebenfalls real, getestet und produktiv ist — nicht, dass die vollständige Migration der bestehenden Anwendung abgeschlossen ist. Nächster Schritt: [Build 024 – STL / STEP Export Workflow](docs/migration/BUILD-024-HANDOFF.md).
