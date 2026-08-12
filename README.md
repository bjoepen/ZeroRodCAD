# ZeroRodCAD

Parametrisches CAD- und Desktop-Projekt für das ZeroRod-System.

ZeroRodCAD erzeugt die Geometrie des ZeroRod-Nullbundsystems, stellt eine interaktive Live-Vorschau
bereit und exportiert Fertigungsdaten als STL, STEP und einen Markdown-Report. Die produktive
Desktop-2.0-Architektur ist **Tauri v2** (WebView-UI, Three.js-3D-Vorschau, Rust-Prozess-/IPC-Schicht,
persistenter Python-3.13-Sidecar, CadQuery/cadquery-ocp-novtk) — evidenzbasiert entschieden
([ADR-022-001](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md), Status: Accepted).

**Build 022** etablierte die produktive Desktop-2.0-Foundation, **Build 023** ergänzte eine
produktive, parametergetriebene Live-Vorschau, und **Build 024** ergänzte einen produktiven,
menschlich validierten Export-Workflow: "Export Model…" öffnet einen nativen macOS-Verzeichnisdialog,
prüft per Preflight auf bestehende Dateien, holt bei Bedarf eine Overwrite-Bestätigung ein und
schreibt STL, STEP und einen Markdown-Report des **aktuell sichtbaren** Modells (nie eines veralteten
Drafts). Alle drei Builds sind vollständig abgeschlossen, jeweils mit Gate PASS und — wo vorgesehen —
menschlicher Validierung durch den Project Owner.

**Wichtig:** Volle Feature-Parität mit der bestehenden PySide6-Anwendung (Projekt-Persistenz,
Settings, Shortcuts, Desktop-Integration) ist noch nicht erreicht — das ist Build 025.
Signing/Notarization folgt in Build 026.

## Was ZeroRodCAD heute kann

- **Parametrische Geometrie**: alle 16 `zerorod-parameters/v1`-Felder (15 geometriewirksam, 1
  Metadatum) editierbar, mit lokaler Validierung und Reset auf kanonische Defaults.
- **Live-Vorschau**: automatisches, debounced Re-Rendering (300 ms) des echten, CadQuery-basierten
  Modells in Three.js — kein manueller "Regenerieren"-Klick nötig.
- **Export**: "Export Model…" exportiert genau das gerade sichtbare, akzeptierte Modell (nie einen
  noch nicht übernommenen Draft) als STL, STEP und Markdown-Report in ein per nativem
  macOS-Verzeichnisdialog gewähltes Ziel — mit Konflikt-Preflight, Overwrite-Bestätigung und
  zweischichtiger Ergebnisverifikation (Sidecar- und Rust-seitig), damit ein unvollständiges oder
  fehlerhaftes Ergebnis niemals als Erfolg erscheint.
- **Persistenter Engine-Prozess**: ein einziger, Rust-verwalteter Python-Sidecar-Prozess bedient
  Vorschau und Export über dieselbe private stdin/stdout-Pipeline — kein Neustart pro Anfrage.

## Architektur

```text
ZeroRodCAD Desktop 2.0
    Tauri v2 (nativer Shell + WebView + Three.js-Vorschau)
    Rust-Prozess-/IPC-Schicht (besitzt den Sidecar-Lebenszyklus vollständig)
    Persistenter Python-3.13-Sidecar (PyInstaller onedir)
        ZeroRodCAD-Engine (unverändert) + CadQuery + cadquery-ocp-novtk
        STL / STEP / Markdown-Report-Export
```

Sicherheitsgrenze: Die WebView erhält keine Shell-, Prozess- oder breite Filesystem-Berechtigung —
nur `core:default` plus die eine, eng begrenzte `dialog:allow-open`-Berechtigung für den nativen
Verzeichnisdialog. Details: [ADR-022-001](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md),
Abschnitt "Security boundary".

Die wichtigsten technischen Eckdaten:

- Python-Standard: **Python >= 3.13,<3.14**
- CadQuery: **2.8.0** mit **cadquery-ocp-novtk 7.9.3.1.1** (kein VTK erforderlich)
- Release-Bundle (Build 024): **~285.9 MiB**, 0 VTK/PySide6/Qt/numba/llvmlite/scipy im produktiven Bundle
- Sidecar-Strategie: persistent + onedir, Cold Start ~0.6 s, Warm Roundtrip ~0.12 s

## Status

```text
Technology Evaluation:                      COMPLETE
Architecture:                               ACCEPTED
Build 022 — Desktop 2.0 Foundation:         COMPLETE (M1-M5, Gate PASS)
Build 023 — Parameters & Live Preview:      COMPLETE (M1-M5, Gate PASS, Human PASS)
Build 024 — STL/STEP Export Workflow:       COMPLETE (M1-M4, Gate PASS, Human PASS)
Build 025 — Desktop Feature Parity:         IN PROGRESS (Discovery PASS, M1 engineering COMPLETE
                                             — Gate BUILD-025-M1: engineering PASS, Human
                                             Validation PENDING)
Next:                                       Build 025 / M1 Human Validation, then M2
```

Build 022 etablierte die produktive Desktop-2.0-Foundation (Tauri-v2-Shell, WebView↔Rust-IPC,
persistenter Sidecar mit Lazy-Start/Timeout/Crash-Recovery, Three.js-Preview-Foundation, produktives
Packaging). Build 023 ergänzte die vollständige Parameter-UI und automatische Live-Vorschau. Build
024 ergänzte den produktiven Export-Workflow (native Dialoge, Preflight, Overwrite, robuste
Fehlerbehandlung, zweischichtige Ergebnisverifikation) — inklusive eines in M2 real durch
menschliche Validierung gefundenen und behobenen Tauri-IPC-Bugs
(`docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md`). Alle drei Builds sind mit Gate PASS und, wo
produktseitig relevant, mit PASS durch den Project Owner abgeschlossen. Details je Build:
[`docs/migration/BUILD-022-COMPLETION.md`](docs/migration/BUILD-022-COMPLETION.md),
[`docs/migration/BUILD-023-COMPLETION.md`](docs/migration/BUILD-023-COMPLETION.md),
[`docs/migration/BUILD-024-COMPLETION.md`](docs/migration/BUILD-024-COMPLETION.md).

Build 025 (Desktop Feature Parity) begann mit einer vollständigen Discovery-Phase
(`docs/migration/BUILD-025-FEATURE-PARITY-MATRIX.md` und Begleitdokumente, Gate PASS) und geht nun
Milestone für Milestone vor. Milestone 1 (Project Persistence) ist engineering-seitig
abgeschlossen: New/Open/Save/Save As gegen das bereits bestehende, unveränderte
`.zerorod`-Projektformat, ein Projekt-Sitzungsmodell mit Dirty-Tracking (`accepted` vs. zuletzt
gespeicherter Zustand) und ein Datenverlust-verhindernder Unsaved-Changes-Guard (Save/Discard/
Cancel) für New, Open und Quit. Details: [`docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md`](docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md).
Human Validation steht noch aus: [`docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md`](docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md).

**Was noch fehlt** (bewusst, spätere Milestones/Builds): native macOS-Menüs, Shortcuts,
Diagnostics-View, Preview-Sichtbarkeits-Toggles, Reset-View, Instrument-Report-Ansicht (Build 025
M2-M4), sowie Signing/Notarization (Build 026). Details:
[`docs/migration/BUILD-025-GAP-REPORT.md`](docs/migration/BUILD-025-GAP-REPORT.md).

Die bisherige PySide6-Anwendung bleibt bis zu einer späteren, ausdrücklichen Retirement-Entscheidung
(frühestens nach Build 026) unverändert als Referenz-, Feature-Parity- und Rollback-Implementierung
erhalten.

## Technologie-Evaluation (Grundlage der Architekturentscheidung)

Bevor die produktive Migration begann, klärte eine Reihe von Technology Evaluations (TE-001 bis
TE-002.2B) evidenzbasiert, ob eine No-VTK/Tauri-Architektur überhaupt funktioniert:

| Evaluation | Ergebnis |
|---|---|
| TE-001 — No-VTK Feasibility | FAIL für unverändertes CadQuery (eager `vtkmodules`-Import) |
| TE-001.1 — CadQuery No-VTK Import Decoupling | PASS — kleiner, reversibler Patch |
| TE-001.2 — No-VTK Production Bundle Proof | Gate C PASS — 910.51 → 380.12 MiB (−58.25 %) |
| TE-002 — Tauri v2 + Sidecar + Three.js | Gate D PASS — vollständige Datenkette bewiesen |
| TE-002.1 — Sidecar-Runtime-Strategie | Gate E-A PASS — persistent + onedir empfohlen |
| TE-002.2A/B — Bundle-Optimierung | Gate F-A/F-B PASS — 293.89 MB / −58.37 % ggü. Baseline |

**Technology Evaluation Phase: COMPLETE.** Volle Details, Messwerte und Rohdaten:
[`docs/research/`](docs/research/) (`TE-001-No-VTK/` bis `TE-002.2B-Tauri-Bundle-Optimization/`).
Der finale ADR: [`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md)
(Status: Accepted, 2026-08-09).

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

### Desktop-App (Tauri)

```bash
cd desktop/frontend && npm install
cd desktop/src-tauri && cargo tauri dev      # Entwicklung
./scripts/build-productive-desktop-app.sh release   # produktiver Release-Build
```

### Bestehende Build-/Analysewerkzeuge

Das Repository enthält umfangreiche Werkzeuge für:

- Bundle Scanner 2.0
- Dependency- und Mach-O-Analyse
- Dead-Library-Analyse
- Bundle Health / Risk Score
- Report Engine
- Analysis Pipeline
- Runtime Trace
- No-VTK Technology Evaluations
- Tauri-/Sidecar-PoCs

Diese Werkzeuge sind ein fester Bestandteil der technischen Entscheidungsfindung und werden für
reproduzierbare Architektur- und Packaging-Nachweise verwendet.

## Repository-Grundsätze

- Python 3.13 ist verbindlicher Standard.
- Neue Dependencies werden vor Aufnahme auf Pflegezustand, Lizenz, Plattformunterstützung und
  tatsächliche Notwendigkeit geprüft.
- Technology Evaluations bleiben im bestehenden Repository; neue Ideen erzeugen nicht automatisch
  neue Repositories.
- Produktive Architekturänderungen werden erst nach reproduzierbarer Evidenz und klar definierten
  Gates beschlossen.
- Bestehende funktionsfähige Referenzpfade werden erst entfernt, wenn eine neue Architektur
  vollständig validiert wurde.

## Dokumentation

Einstiegspunkt für die vollständige Migrations- und Build-Dokumentation:
[`docs/migration/README.md`](docs/migration/README.md) — verlinkt jeden Build- und
Meilenstein-Report, den ADR, und die Vertragsdokumentation
([`docs/contracts/ZEROROD-PARAMETERS-V1.md`](docs/contracts/ZEROROD-PARAMETERS-V1.md)).

Research-Rohdaten der Technology Evaluations liegen unter [`docs/research/`](docs/research/).
