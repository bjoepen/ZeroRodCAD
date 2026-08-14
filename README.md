# ZeroRodCAD

Parametrisches CAD- und Desktop-Projekt für das ZeroRod-System.

ZeroRodCAD erzeugt die Geometrie des ZeroRod-Nullbundsystems, stellt eine interaktive Live-Vorschau
bereit und exportiert Fertigungsdaten als STL, STEP und einen Markdown-Report. Die produktive
Desktop-2.0-Architektur ist **Tauri v2** (WebView-UI, Three.js-3D-Vorschau, Rust-Prozess-/IPC-Schicht,
persistenter Python-3.13-Sidecar, CadQuery/cadquery-ocp-novtk) — evidenzbasiert entschieden
([ADR-022-001](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md), Status: Accepted).

**Build 022** etablierte die produktive Desktop-2.0-Foundation, **Build 023** ergänzte eine
produktive, parametergetriebene Live-Vorschau, **Build 024** ergänzte einen produktiven,
menschlich validierten Export-Workflow, und **Build 025** ergänzte Projekt-Persistenz
(New/Open/Save/Save As gegen das bestehende `.zerorod`-Format), ein produktiviertes Lifecycle-UI
(automatische Initial-Preview, Diagnostics-View), Preview-/Report-Parität (Reset View,
Body/Rod/Strings-Sichtbarkeit, In-App Instrument Report) und eine native macOS-Desktop-Shell
(Application/File/View-Menü, ⌘N/⌘O/⌘S/⇧⌘S/⌘Q, natives About) — inklusive der Behebung der
Quit/⌘Q-Guard-Bypass-Lücke, sodass natives Beenden jetzt denselben Save/Discard/Cancel-Schutz
durchläuft wie der rote Schließen-Knopf. "Export Model…" öffnet einen nativen
macOS-Verzeichnisdialog, prüft per Preflight auf bestehende Dateien, holt bei Bedarf eine
Overwrite-Bestätigung ein und schreibt STL, STEP und einen Markdown-Report des **aktuell
sichtbaren** Modells (nie eines veralteten Drafts). Alle vier Builds sind vollständig
abgeschlossen, jeweils mit Gate PASS und — wo vorgesehen — menschlicher Validierung durch den
Project Owner.

**Wichtig:** Desktop-Feature-Parität mit der bestehenden PySide6-Anwendung ist im mit Build 025
freigegebenen Umfang erreicht (Projekt-Persistenz, Lifecycle, Preview/Report, native Menüs/
Shortcuts). Settings, Recent Files, Drag & Drop, Datei-Assoziationen sowie Signing/Notarization
folgen erst in Build 026 bzw. einer späteren, ausdrücklichen Freigabe.

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
  Vorschau, Export, Report und Projekt-I/O über dieselbe private stdin/stdout-Pipeline — kein
  Neustart pro Anfrage. Der Benutzer startet oder verwaltet die Engine nie manuell.
- **Projekt-Persistenz**: New/Open/Save/Save As gegen das bestehende, unveränderte
  `.zerorod`-Format, mit Dirty-Tracking und einem Datenverlust-verhindernden
  Save/Discard/Cancel-Guard für New, Open und Quit/Fenster schließen.
- **View-Controls & Report**: Reset View, Body/Rod/Strings-Sichtbarkeit (überlebt einen
  Live-Vorschau-Refresh) und ein In-App Instrument Report, byte-identisch zum Export-Report für
  denselben akzeptierten Zustand.
- **Native macOS-Desktop-Shell**: ein natives Application/File/View-Menü (kein Tauri-Standardmenü),
  native Tastenkürzel (⌘N/⌘O/⌘S/⇧⌘S/⌘Q), natives About, und ein Diagnostics-View für
  Engine-/Sidecar-Status. Natives ⌘Q und der rote Schließen-Knopf laufen durch denselben
  Save/Discard/Cancel-Guard.

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
nur `core:default` plus drei eng begrenzte Zusatzrechte: `dialog:allow-open`/`dialog:allow-save`
für die nativen Datei-/Verzeichnisdialoge (Export-Ziel, Projekt-Open/Save) und
`core:window:allow-destroy` für den geführten Fenster-Schließen-Ablauf. Details:
[ADR-022-001](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md), Abschnitt "Security
boundary".

Die wichtigsten technischen Eckdaten:

- Python-Standard: **Python >= 3.13,<3.14** — produktives Packaging nutzt gepinntes, portables
  CPython 3.13.15 (`astral-sh/python-build-standalone`, checksum-verifiziert), kein Homebrew
- CadQuery: **2.8.0** mit **cadquery-ocp-novtk 7.9.3.1.1** (kein VTK erforderlich)
- Release-Bundle (Build 026): **~310 MiB** (arm64, macOS 11.1+), 0 VTK/PySide6/Qt/numba/llvmlite/scipy im produktiven Bundle
- Sidecar-Strategie: persistent + onedir, Cold Start ~0.6 s, Warm Roundtrip ~0.12 s

## Status

```text
Technology Evaluation:                      COMPLETE
Architecture:                               ACCEPTED
Build 022 — Desktop 2.0 Foundation:         COMPLETE (M1-M5, Gate PASS)
Build 023 — Parameters & Live Preview:      COMPLETE (M1-M5, Gate PASS, Human PASS)
Build 024 — STL/STEP Export Workflow:       COMPLETE (M1-M4, Gate PASS, Human PASS)
Build 025 — Desktop Feature Parity:         COMPLETE (M1-M5, Gate PASS, Human PASS)
Build 026 — Production Packaging:           FINALIZATION ENGINEERING COMPLETE, Human Validation PENDING
Next:                                       Human Validation of the Release Candidate; real signing/
                                             notarization remain credential-gated, not yet authorized
```

Build 022 etablierte die produktive Desktop-2.0-Foundation (Tauri-v2-Shell, WebView↔Rust-IPC,
persistenter Sidecar mit Lazy-Start/Timeout/Crash-Recovery, Three.js-Preview-Foundation, produktives
Packaging). Build 023 ergänzte die vollständige Parameter-UI und automatische Live-Vorschau. Build
024 ergänzte den produktiven Export-Workflow (native Dialoge, Preflight, Overwrite, robuste
Fehlerbehandlung, zweischichtige Ergebnisverifikation) — inklusive eines in M2 real durch
menschliche Validierung gefundenen und behobenen Tauri-IPC-Bugs
(`docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md`). Build 025 ergänzte Projekt-Persistenz, ein
produktiviertes Lifecycle-UI, Preview-/Report-Parität und eine native macOS-Desktop-Shell — siehe
unten. Alle vier Builds sind mit Gate PASS und, wo produktseitig relevant, mit PASS durch den
Project Owner abgeschlossen. Details je Build:
[`docs/migration/BUILD-022-COMPLETION.md`](docs/migration/BUILD-022-COMPLETION.md),
[`docs/migration/BUILD-023-COMPLETION.md`](docs/migration/BUILD-023-COMPLETION.md),
[`docs/migration/BUILD-024-COMPLETION.md`](docs/migration/BUILD-024-COMPLETION.md),
[`docs/migration/BUILD-025-COMPLETION.md`](docs/migration/BUILD-025-COMPLETION.md).

Build 025 (Desktop Feature Parity) begann mit einer vollständigen Discovery-Phase
(`docs/migration/BUILD-025-FEATURE-PARITY-MATRIX.md` und Begleitdokumente, Gate PASS) und ist jetzt
**vollständig abgeschlossen**. Milestone 1 (Project Persistence): New/Open/Save/Save As gegen das
bereits bestehende, unveränderte `.zerorod`-Projektformat, ein Projekt-Sitzungsmodell mit
Dirty-Tracking (`accepted` vs. zuletzt gespeicherter Zustand) und ein
Datenverlust-verhindernder Unsaved-Changes-Guard (Save/Discard/Cancel) für New, Open und Quit —
Human Validation PASS. Milestone 2 (Product UI Productization & Lifecycle Polish): automatische
Initial-Preview, ein Diagnostics-View für die alten technischen Engine/Ping-Controls — Human
Validation PASS. Milestone 3 (Preview & Report Parity): Reset View, Body/Rod/Strings-Sichtbarkeit,
In-App Instrument Report — Human Validation PASS. Milestone 4 (Desktop Shell & Native Integration):
natives Application/File/View-Menü, native Shortcuts, natives About, und die Behebung der
Quit/⌘Q-Guard-Bypass-Lücke (natives ⌘Q läuft jetzt durch denselben Guard wie der rote
Schließen-Knopf) — Human Validation PASS. Milestone 5 (Integration, Completion & Repository
Cleanup): Konsistenzaudit, Repository-Cleanup-Discovery (0 sicher entfernbare Code-/Skript-Kandidaten
gefunden), Architektur-Konformitätsprüfung, vollständiger Test-Re-Run, sauberer reproduzierbarer
Release-Rebuild und das Master-Gate `scripts/validate-build025.sh` (`BUILD-025 CONSISTENCY GATE:
PASS`). Details je Milestone in [`docs/migration/README.md`](docs/migration/README.md) und
[`docs/migration/BUILD-025-COMPLETION.md`](docs/migration/BUILD-025-COMPLETION.md).

**Was noch fehlt** (bewusst, spätere Builds): Settings, Recent Files, Drag & Drop,
Datei-Assoziationen/Finder-Integration, und die PySide6-Retirement-Entscheidung (frühestens nach
Build 026).

**Build 026 (Production Packaging & macOS Integration)** ist als eine kontrollierte
Finalisierungs-Sequenz abgeschlossen (Discovery → M1 Production-Bundle-Hardening → M1.1
Portable-Python-Research → Finalisierung), auf ausdrücklichen Wunsch des Project Owners ohne weitere
Meilenstein-Zersplitterung. Portables, gepinntes CPython 3.13
(`astral-sh/python-build-standalone`, checksum-verifiziert, kein Homebrew) ersetzt die
Build-Umgebung; ein voller Bundle-Scan bestätigt macOS **11.1** als ehrliche, gemessene
Mindestversion (OpenCASCADE ist die bindende Komponente — nicht die zunächst angenommene macOS 11,
aber weit unter dem zuvor gemessenen, Homebrew-bedingten 26.0). Primäres Distributionsartefakt ist
eine DMG (`ZeroRodCAD-0.1.0-macOS-arm64.dmg`); Signing-/Notarization-Infrastruktur ist vorbereitet
(Skripte, korrekte Signierreihenfolge, keine Echt-Credentials) und bleibt explizit
credential-gated. Master-Gate: `scripts/validate-build026.sh` (`BUILD-026 CONSISTENCY GATE: PASS`).
Details: [`docs/migration/BUILD-026-COMPLETION.md`](docs/migration/BUILD-026-COMPLETION.md).

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
