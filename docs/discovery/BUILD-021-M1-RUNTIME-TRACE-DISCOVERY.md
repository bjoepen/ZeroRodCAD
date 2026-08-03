# Build 021 M1 – Runtime Trace Foundation: Repository Discovery

Status: Phase 0 / Discovery, keine Implementierung
Erhebungsdatum: 2026-08-03
Branch: `feature/build021-m1-runtime-trace-foundation`
Baseline-Commit: `ac9078f Merge pull request #10 from bjoepen/feature/build020-m4-performance-release`

## 1. Executive Summary

Build 020 liefert einen GUI-freien Analysis Core mit einer einmalig ausgeführten
`AnalysisPipeline`, einer getrennten `ReportEngine` und konservativer
Confidence-/Recommendation-Logik. Die statische Dead-Library-Analyse besitzt bereits die
Evidenzarten `DYNAMIC_LOAD`, `DYNAMIC_LOAD_HINT` und `PLUGIN_MANIFEST`; aktuell entstehen jedoch
nur syntaktische Importbelege, Mach-O-Belege und einfache Text-Hinweise auf
`importlib.import_module` oder `dlopen`. Beobachtete Laufzeitbelege werden nicht erhoben oder in
einem stabilen Schema gespeichert.

Es existieren wiederverwendbare Vorarbeiten: `tools/trace_runtime_imports.py` erfasst nach einem
Desktop-Lauf geladene `vtkmodules` aus `sys.modules`, `scripts/runtime_import_probe.py` prüft eine
feste Modulliste, Packaging und Verifikation starten die Anwendung kontrolliert, und der bestehende
PyInstaller-Runtime-Hook setzt den Qt-Plug-in-Pfad. Keiner dieser Bausteine bildet allein einen
vollständigen, read-only Runtime Trace.

Für Phase 1 wird deshalb eine hybride, explizit aktivierte Lösung empfohlen:

1. plattformneutrale Trace-Modelle, Normalisierung, Zusammenführung und deterministische
   Serialisierung unter `src/zerorod_analysis/runtime/`;
2. ein macOS-Controller unter `tools/trace_runtime.py`, der das Bundle als Subprozess mit Timeout
   und explizitem externem Ausgabeziel startet;
3. Erweiterung des vorhandenen `packaging/macos/runtime_hook.py` um einen ausschließlich per
   Umgebungsvariable aktivierten Audit-/Import-Recorder;
4. ergänzende Erfassung von dyld- und Qt-Diagnoseausgaben durch den Controller;
5. Weiterleitung oder Ablösung des bisherigen VTK-Spezialwerkzeugs ohne parallele Trace-Logik.

Der normale App-Start bleibt bei deaktivierter Trace-Umgebung unverändert. M1 sammelt nur Evidenz;
eine spätere Verwendung für Empfehlungen gehört in M2 und darf Risk Score oder Bundle Health in M1
nicht ändern.

## 2. Untersuchte Repository-Bereiche

### Repository und Baseline

- Aktiver Branch: `feature/build021-m1-runtime-trace-foundation`.
- Der Working Tree war vor der Discovery sauber.
- Letzter Commit: `ac9078f` (Merge des Build-020-M4-Branches).
- Ausgeführtes Python: CPython 3.13.14; `pyproject.toml` fordert `>=3.13,<3.14`.
- Die Suche ab dem übergeordneten Verzeichnis fand keine `AGENTS.md` oder
  `AGENTS.override.md`; es waren daher keine zusätzlichen Repository-Anweisungen anzuwenden.

### Build 020 Analysis Core

- `src/zerorod_analysis/__init__.py` exportiert ausschließlich `analyze_bundle`,
  `generate_reports`, `generate_action_plan` und `calculate_bundle_health`.
- `src/zerorod_analysis/api.py` erstellt für `analyze_bundle()` einen `PipelineContext` und ruft
  `AnalysisPipeline.default().run(context)` auf.
- `src/zerorod_analysis/pipeline/pipeline.py` ordnet `ScannerStage`, `MachOStage`,
  `DeadLibraryStage` und `AdvisorStage`; die Stages werden einmal in dieser Reihenfolge ausgeführt.
- `src/zerorod_analysis/report/engine.py` hält Reporting von Analyse getrennt und registriert
  JSON-, Markdown- und DOT-Renderer explizit.
- `tools/bundle_analyzer/**` besteht, abgesehen von der historischen CLI, aus delegierenden
  Compatibility-Fassaden. Die vorhandenen Rückwärtskompatibilitätstests prüfen Objektidentität und
  verbieten neue Fachdefinitionen in diesen Fassaden.

### Dead-Library-, Confidence- und Recommendation-Logik

- `src/zerorod_analysis/deadlibs/resolver.py::_python_imports()` erfasst statische `ast.Import`-
  und `ast.ImportFrom`-Knoten. Dynamisch berechnete Modulnamen sind damit nicht sichtbar.
- `resolve_usage()` erzeugt einen `DYNAMIC_LOAD_HINT`, wenn ein Bibliotheksname in einer
  Textdatei zusammen mit `importlib.import_module` oder `dlopen` vorkommt. Es führt keinen Code aus
  und beobachtet keinen Loader.
- `src/zerorod_analysis/deadlibs/models.py` definiert bereits `PLUGIN_MANIFEST`, `DYNAMIC_LOAD` und
  `DYNAMIC_LOAD_HINT`; für echte Runtime-Ereignisse fehlt die Datenquelle.
- `src/zerorod_analysis/deadlibs/confidence.py::assess_usage()` stuft dynamische oder unaufgelöste
  Hinweise als `LOW`/`REVIEW`, statische Referenzen als `HIGH`/`KEEP` und unreferenzierte Dylibs
  beziehungsweise Frameworks ansonsten als `HIGH`/`SAFE_REMOVE` ein.
- `src/zerorod_analysis/deadlibs/advisor.py::RiskEvaluator` erhöht das Risiko für dynamische Loads
  und Plug-in-Manifeste; `RecommendationAdvisor` empfiehlt bei `REVIEW` bereits, Runtime-Import-
  oder Loader-Traces zu sammeln.

Diese Logik erklärt die aktuelle Fehlklassifikationsgefahr: Die Modelle können Laufzeitbelege
ausdrücken, aber die Pipeline liefert sie noch nicht.

### Desktop-, CAD- und Packaging-Pfade

- PyInstaller startet `src/zerorodcad_desktop/launcher.py`; dieser delegiert an
  `zerorodcad_desktop.app.main()`.
- `src/zerorodcad_desktop/app.py` importiert PySide6 und `MainWindow` auf Modulebene, konfiguriert
  Logging und den Exception-Hook und unterstützt `--diagnose` sowie `--startup-test`.
- `src/zerorodcad_desktop/main_window.py` erzeugt die Preview asynchron über `PreviewJob` und ruft
  für den Export `zerorodcad.export.export_project()` auf.
- `src/zerorodcad_desktop/workers.py::PreviewJob.run()` importiert
  `zerorodcad.preview.build_preview_scene` bewusst erst im Worker. Dadurch werden CadQuery/OCP erst
  beim Preview-Workflow geladen.
- `src/zerorodcad/preview.py` und `src/zerorodcad/model.py` importieren CadQuery; CadQuery bindet
  OCP/Open Cascade ein. Die Preview tesselliert CadQuery-Solids und rendert anschließend über das
  eigene PySide6/QPainter-Widget, nicht über einen VTK-Widget-Import im Anwendungscode.
- `src/zerorodcad/export.py::export_project()` importiert `cadquery.exporters` und die
  Modellfunktionen absichtlich lazy. Es schreibt STL über `exporters.export()` und STEP über
  `Assembly.export()` sowie einen Markdown-Projektbericht in das vom Benutzer gewählte Ziel.
- Außer dem Stringtest in `deadlibs/resolver.py` wurden in produktivem Quellcode keine direkten
  `ctypes`, `cffi`, `CDLL`, `PyDLL`, `QLibrary` oder `QPluginLoader`-Aufrufe gefunden. Native Loads
  können dennoch innerhalb von PySide6, CadQuery, OCP und deren Erweiterungsmodulen stattfinden.
- `packaging/macos/ZeroRodCAD.spec` verwendet den Launcher, führt ausgewählte OCP/CadQuery/VTK-
  Hidden Imports und den bestehenden `runtime_hook.py` auf. Der Hook setzt im Frozen-Modus
  `QT_PLUGIN_PATH` auf das gebündelte PySide6-Plug-in-Verzeichnis.
- Die Spec enthält zugleich `casadi` als Hidden Import, während die historische
  Dependency-Audit-Dokumentation CasADi als ausgeschlossen beschreibt. Diese Inkonsistenz ist für
  M1 nicht zu ändern, muss bei Interpretation eines Traces aber berücksichtigt werden.

### Konstanten und Schemas

| Konstante | Maßgebliche Quelle | Aktueller Wert |
| --- | --- | --- |
| Analyzer-Build-ID | `src/zerorod_analysis/build_metadata.py` | `020-M4` |
| Scanner-/Benchmark-Namen | `src/zerorod_analysis/build_metadata.py` | zentrale Konstanten |
| Report-Schema | `src/zerorod_analysis/report/models.py` | `zerorod-analysis/report/v1` |
| Benchmark-Schema | `src/zerorod_analysis/metrics.py` | `zerorod-analysis/benchmark/v1` |
| Scanner-Cache-Version | `src/zerorod_analysis/scanner/cache.py` | `2` |
| Dead-Library-JSON-Version | `src/zerorod_analysis/deadlibs/report.py` | `2` |
| Desktop-App-Version/-Build | `src/zerorodcad_desktop/application_info.py` | `0.15.0` / `015` |

Die PyInstaller-Spec und `scripts/package_macos_release.sh` wiederholen die Desktop-Version
zusätzlich. Analyzer-Build und Desktop-Release sind derzeit getrennte Begriffe. Phase 1 darf die
Build-021-ID nicht erneut in Tool, Hook und Schema duplizieren: Sie muss aus
`zerorod_analysis.build_metadata` kommen. Die Trace-Schema-ID benötigt ebenfalls genau eine
maßgebliche Definition im neuen Runtime-Paket.

## 3. Vorhandene wiederverwendbare Komponenten

### `tools/trace_runtime_imports.py`

- **Zweck:** startet `zerorodcad_desktop.launcher` über `runpy` und schreibt bei Prozessende die
  geladenen Namen `vtkmodules`/`vtkmodules.*` aus `sys.modules`.
- **Eingaben:** keine CLI-Argumente; verwendet das Source-Repository.
- **Ausgabe:** fest verdrahtet nach
  `build/reports/sprint3-phase3-vtk-analysis/vtkmodules-runtime-loaded.txt` und auf stdout.
- **Abhängigkeiten:** nur Standardbibliothek plus vollständiger Desktop-Start.
- **Wiederverwendung:** Filter-/Sortieridee und Snapshot nach einem Lauf sind brauchbar; Start,
  Datenmodell und Dateiausgabe müssen an eine gemeinsame Trace-Infrastruktur delegieren.
- **Grenzen:** nur VTK-Namen, keine Ereigniszeit, fehlgeschlagenen Imports, nativen Libraries oder
  Qt-Plug-ins; keine Timeout-Steuerung; fester Repository-Schreibpfad; interaktiver Lauf kann bis
  zum App-Ende dauern; `atexit` ist bei harter Beendigung nicht verlässlich.
- **Tests:** keine direkte Testreferenz gefunden.

### `scripts/runtime_import_probe.py`

- **Zweck:** importiert eine feste Liste aus PySide6, CadQuery, OCP, VTK, Core und Desktop über
  `importlib.import_module` und meldet `OK`/`FAIL`.
- **Eingaben:** keine; feste `MODULES`-Konstante.
- **Ausgabe:** Text auf stdout, Exit 1 bei mindestens einem Fehler.
- **Verwendung:** `scripts/audit_dependencies.sh` protokolliert die Ausgabe; der macOS-Build führt
  den Probe vor PyInstaller aus.
- **Wiederverwendung:** geeigneter deterministischer Stimulus und Packaging-Smoke-Test.
- **Grenzen:** beweist nur, dass genau diese Imports in der Source-/Packaging-Umgebung gelingen;
  er verfolgt keine reale Benutzeraktion und zeichnet transitive Loader-Ereignisse nicht auf.
- **Tests:** `tests/test_packaging_files.py` prüft nur die Existenz des Skripts.

### `scripts/verify_preview_engine.py`

- **Zweck:** erzeugt headless eine Standard-Preview und validiert nichtleere Meshes.
- **Ausgabe:** `PREVIEW_ENGINE_OK` plus Strukturzahlen; Exceptions führen zu Fehlerstatus.
- **Wiederverwendung:** reproduzierbarer Preview-Workflow für Source-Traces und Integrationstests.
- **Grenzen:** kein Qt-App-Start, keine Interaktion und kein STL-/STEP-Export; keine eigene
  Timeout- oder Trace-Ausgabe.
- **Tests:** keine direkte Testdatei; die Preview-Fachlogik ist separat in `test_preview*.py`
  abgedeckt.

### `scripts/verify_macos_app.sh`

- **Zweck:** führt Diagnose, offscreen Startup-Test, Source-Preview, Plist-, Größen- und
  Verdachtsreport-Prüfungen aus und öffnet anschließend die App interaktiv.
- **Eingabe:** optionaler `.app`-Pfad.
- **Wiederverwendung:** bekannte Startbefehle `--diagnose`, `--startup-test` und
  `QT_QPA_PLATFORM=offscreen`.
- **Grenzen:** schreibt mehrere Reports, öffnet die App ohne Timeout und verlangt manuelle Preview-
  und Exportkontrolle. Es ist daher kein read-only Trace-Controller.
- **Tests:** keine direkte Testreferenz gefunden.

### `scripts/audit_dependencies.sh`

- **Zweck:** installiert Audit-Werkzeuge in der Packaging-Venv und schreibt Paketbaum,
  Paketgrößen und den Import-Probe nach `build/reports/dependencies`.
- **Wiederverwendung:** liefert statischen Kontext für spätere Trace-Auswertung.
- **Grenzen:** verändert die Packaging-Umgebung, benötigt zusätzliche Entwicklungswerkzeuge und
  beobachtet keinen gebündelten App-Prozess.
- **Tests:** `tests/test_packaging_files.py` prüft nur die Existenz.

### `scripts/report_suspect_dependencies.sh`

- **Zweck:** sucht im Bundle per Dateiname nach einer festen Liste schwerer Abhängigkeiten.
- **Ausgabe:** `build/reports/suspect-dependencies.txt` und stdout.
- **Wiederverwendung:** statischer Gegencheck zu beobachteten Komponenten.
- **Grenzen:** Namenssuche ist weder Import- noch Load-Nachweis und erzeugt False Positives wie
  False Negatives.
- **Tests:** `tests/test_packaging_files.py` prüft nur die Existenz.

### Weitere Diagnosebausteine

- `src/zerorodcad_desktop/diagnostics.py` meldet Plattform, Python, Executable, Frozen-Status und
  Paketversionen, prüft dabei aber durch eine Probe-Datei die Schreibbarkeit des Home-Verzeichnisses.
  Es ist Kontextquelle, aber nicht unverändert als read-only Trace-Schritt geeignet.
- `scripts/analyze_pyinstaller_build.sh` sammelt Warn-, XRef- und Graph-Artefakte sowie
  Frameworkgrößen. Diese Daten erklären statische Collection, nicht tatsächliche Laufzeitnutzung.
- Die Build-020-Metriken messen Pipeline-Stages und Renderer; sie sind pro Run, beobachten aber
  keine App-Imports oder nativen Loader.

## 4. Aktuelle Lücken

1. Es gibt kein gemeinsames Trace-Schema und keinen typisierten Run-Status.
2. Python-Importe werden nur statisch beziehungsweise als abschließender VTK-Snapshot erfasst.
3. Fehlgeschlagene, dynamische und transitive Imports besitzen keinen Laufzeitnachweis.
4. Native Extension-Module, Dylibs, Frameworks und Qt-Plug-ins werden nicht beobachtet.
5. Die vorhandenen Werkzeuge haben kein gemeinsames externes Ausgabeziel, Timeout- und
   Cleanup-Konzept.
6. Ein Trace ist weder auf Bundle-relative Pfade normalisiert noch gegen dauerhafte Speicherung
   privater Benutzerpfade abgesichert.
7. Es gibt keine Tests für Traces, unvollständige Prozesse oder unveränderte App-Bundles.
8. Es gibt noch keine definierte Übergabe von Runtime-Evidenz an eine spätere M2-Auswertung.
9. `--startup-test` deckt nur Fensterkonstruktion ab; der Preview-Worker und der lazy Exportpfad
   werden dadurch nicht zwingend ausgeführt.
10. Der GUI-Start schreibt regulär ein Log unter dem Benutzerprofil. Das verändert nicht das
    analysierte Bundle, muss für reproduzierbare Tests aber über isoliertes `HOME` beziehungsweise
    eine explizite Testumgebung kontrolliert werden.

## 5. Bewertung der Trace-Techniken

| Methode | Erfasst | Erfasst nicht / Grenzen | Verhalten, Kompatibilität, Tests und Datenschutz |
| --- | --- | --- | --- |
| `sys.addaudithook()` | Audit-Ereignisse nach Installation, insbesondere Import- und je nach aufrufender API `ctypes.dlopen`-/Subprozess-Ereignisse | Ereignisse vor Hook-Installation; fremde native Loads ohne passendes Python-Audit-Ereignis; andere Prozesse | Kleine, synchrone Zusatzkosten je Ereignis. In Frozen-Apps früh über den bestehenden Runtime-Hook installierbar. Hook kann nicht entfernt werden, daher nur in einem dedizierten Trace-Prozess aktivieren. Argumente können absolute Pfade enthalten und müssen vor Persistenz normalisiert werden. Gut mit Subprozess-Fixtures testbar. |
| `MetaPathFinder` | Auflösungsversuche, die den Python-Meta-Path durchlaufen | bereits geladene Module, native `dlopen`-Vorgänge, Qt-Plug-ins und möglicherweise vom Frozen Importer intern behandelte Details | Ein zusätzlicher Finder kann Reihenfolge/Fehlerverhalten beeinflussen und mit PyInstallers Frozen Importer interagieren. Als Primärtechnik unnötig invasiv; höchstens gezielter Testadapter. |
| `sys.modules`-Snapshots | am Snapshot-Zeitpunkt vorhandene Python-Module einschließlich Namen nativer Extension-Module | Zeitpunkt, Anzahl, fehlgeschlagene oder inzwischen entfernte Imports; direkt geladene Dylibs und Plug-ins ohne Modul | Sehr geringe Invasivität und bereits im VTK-Werkzeug erprobt. Start-/End-Differenz und Moduldatei-Suffix können Audit-Daten ergänzen. Pfade aus `module.__file__` normalisieren. |
| Importlib-Instrumentierung | explizite Aufrufe über die instrumentierte Importlib-Funktion | normale Import-Statements, alternative Loader, C-Level- und Qt-Loads; frühe Imports | Das Ersetzen von Importlib-Funktionen verändert globale Prozesssemantik. Der aktuelle Probe zeigt nur aktive Testimporte. Nicht als Produktions-Recorder empfehlen. |
| `DYLD_PRINT_LIBRARIES` | vom dyld des gestarteten Prozesses gemeldete Images/Dylibs/Frameworks | Python-Modulsemantik, Begründung eines Loads; Verhalten kann durch macOS-Sicherheitskontext variieren | Nur macOS. Als Umgebungsvariable am kontrollierten Subprozess ohne Bundle-Änderung nutzbar; Ausgabe ist laut und enthält System-/Benutzerpfade. Parser mit gespeicherten Fixtures testen, Pfade redigieren. Auf signierten/hardened Builds praktisch verifizieren, nicht theoretisch voraussetzen. |
| `vmmap` | Momentaufnahme gemappter Images eines laufenden PID | abgeschlossene/transiente Loads, Python-Importursache; kann durch Berechtigungen eingeschränkt sein | macOS-spezifisch, extern und read-only, aber timingabhängig. Als optionale Diagnose/Fallback, nicht als deterministische Pflichtquelle. Parser und Fehlerpfad über Fixtures testen. |
| `otool` / `dyld_info` | statische Load Commands, IDs, RPaths beziehungsweise dyld-Metadaten | tatsächlich zur Laufzeit gewählte Pfade und dynamisch nachgeladene Komponenten | Read-only und bereits nutzt der Core `otool -L/-D`. Als statischer `inferred`-Beleg und Abgleich geeignet, nicht als Runtime Trace. Toolverfügbarkeit und Architekturen beachten. |
| `QT_DEBUG_PLUGINS` | Qt-Plug-in-Suche, Kandidaten, Metadaten, Ladefehler und erfolgreiche Loads auf stderr | Nicht-Qt-Loads; Ausgabeformat ist Qt-versionsabhängig | Sehr passend, weil der bestehende Runtime-Hook `QT_PLUGIN_PATH` setzt. Nur im Trace-Subprozess aktivieren. Absolute Suchpfade und umfangreiche Metadaten normalisieren. Parser mit kontrollierten Log-Fixtures testen; eine echte macOS-Integration separat kennzeichnen. |
| Subprozess-basierter App-Start | Exit-Code, stdout/stderr, Umgebungsdiagnosen, Timeout und Prozesslebenszyklus | interne semantische Ereignisse ohne Hook oder Diagnosevariable | Empfohlene Kontrollschicht. Prozessgruppe starten, zunächst regulär beenden und nach Schonfrist hart beenden; Timeout als unvollständigen Trace markieren. Externes Temp-/Zielverzeichnis und isolierte Umgebung ermöglichen Tests. |
| Direkte Launcher-Instrumentierung | sehr frühe app-spezifische Python-Ereignisse im Source-Start | PyInstaller-Bootstrap vor dem Launcher und rein native Loads | Würde normalen Anwendungscode mit Diagnosebelangen koppeln. Nicht erforderlich, wenn der vorhandene Runtime-Hook opt-in erweitert wird. Source-Traces können über einen kleinen Trace-Bootstrap erfolgen. |
| PyInstaller-Runtime-Hook | Installation vor dem Launcher im Frozen-Prozess, Audit-Hook und Start-Snapshot | PyInstaller-Bootloader-Ereignisse vor Python-Hook sowie externe Loader ohne Zusatzquelle | Beste Stelle für opt-in Frozen-Instrumentierung. Vorhandenen Hook erweitern, keine zweite Hook-Datei oder Spec-Variante schaffen. Ohne Trace-Umgebungsvariable nur die bestehende Qt-Pfadlogik ausführen. |

### Auswahl

Keine Einzeltechnik deckt die vier benötigten Ebenen ab. Empfohlen ist:

- Audit-Hook plus Start-/End-`sys.modules`-Snapshot für Python;
- `DYLD_PRINT_LIBRARIES` für beobachtete native Loader-Ausgabe, mit optionalem `vmmap`-Fallback;
- `QT_DEBUG_PLUGINS` für Qt;
- bestehendes `otool`/PyInstaller-XRef nur als klar gekennzeichnete `inferred`-Quelle;
- ein Subprozess-Controller für Grenzen, Timeout, Exit und sichere Dateiausgabe.

## 6. Empfohlene Architektur

```text
tools/trace_runtime.py (macOS Controller)
    |
    +-- startet Bundle mit expliziter Trace-Umgebung und Timeout
    +-- sammelt stdout/stderr, dyld- und Qt-Diagnose
    +-- fordert Hook-Ausgabe in temporärem externem Verzeichnis an
    |
    v
packaging/macos/runtime_hook.py (nur opt-in erweitert)
    |
    +-- sys.addaudithook
    +-- sys.modules Start-/End-Snapshot
    +-- rohe Prozess-Ereignisse außerhalb des Bundles
    |
    v
src/zerorod_analysis/runtime/
    +-- models.py       # reine Dataclasses/Enums
    +-- schema.py       # eine TRACE_SCHEMA_ID
    +-- normalize.py    # Bundle-relative/redigierte Identitäten
    +-- merge.py        # Deduplizierung, Status und Zähler
    +-- serialization.py# deterministisches JSON
```

### Verantwortungsgrenzen

- **Analysis Core:** nur plattformneutrale Datenmodelle, Normalisierung, Merge und
  Serialisierung. Keine PySide6-Imports, kein App-Start und keine macOS-Befehle. Das Runtime-Paket
  bleibt intern und wird in M1 nicht zu einem fünften Top-Level-Export.
- **Tool:** Prozesssteuerung, macOS-Umgebungsvariablen, Parser für dyld/Qt und optionale externe
  Werkzeuge. Direkter Skript- und Modulaufruf sollen dieselbe Implementierung verwenden.
- **App/Packaging:** keine Instrumentierung in `app.py` oder `launcher.py`. Den vorhandenen
  PyInstaller-Runtime-Hook ausschließlich bei einer eindeutig benannten Trace-Umgebungsvariable
  erweitern. Damit bleibt der normale Startpfad unverändert.
- **Vorhandene Werkzeuge:** `tools/trace_runtime_imports.py` soll nach Einführung des Controllers
  entweder als Compatibility-Einstieg an diesen delegieren oder nach dokumentierter Migration
  entfallen; es darf keine zweite Recorder-Logik behalten. `runtime_import_probe.py` und
  `verify_preview_engine.py` bleiben Stimuli/Smokes.
- **M2-Anschluss:** M1 schreibt ausschließlich Trace-Daten. M2 kann eine separate Import-/Mapping-
  Schicht vorsehen, die `observed`-Evidenz in vorhandene `ReferenceKind`-Werte überführt. Diese
  Schicht muss unaufgelöste Zuordnungen erhalten und darf nicht automatisch Dateien entfernen.

### Workflow-Abdeckung

Ein bloßer Startup-Trace reicht wegen der lazy Preview- und Exportimporte nicht. Phase 1 sollte
mindestens klar benannte Profile unterstützen: `startup-test`, `preview-probe` und `export-probe`.
Ob der echte GUI-Prozess Benutzeraktionen automatisieren soll, bleibt offen; bevorzugt werden die
vorhandenen headless Stimuli, solange sie nachweislich dieselben Fachpfade ausführen.

## 7. Vorgeschlagenes Datenmodell

Die Modelle führen keine Messung und keine Dateioperationen aus.

```python
class EvidenceStatus(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"

class EvidenceKind(StrEnum):
    PYTHON_MODULE = "python-module"
    NATIVE_EXTENSION = "native-extension"
    DYLIB = "dylib"
    FRAMEWORK = "framework"
    QT_PLUGIN = "qt-plugin"

@dataclass(frozen=True, slots=True)
class TraceEvidence:
    identity: str
    kind: EvidenceKind
    status: EvidenceStatus
    sources: tuple[str, ...]
    event_count: int
    bundle_relative_path: str | None = None

@dataclass(frozen=True, slots=True)
class RuntimeTrace:
    schema: str
    build_id: str
    python_version: str
    platform: str
    started_at: str
    ended_at: str
    exit_status: str
    exit_code: int | None
    timed_out: bool
    incomplete: bool
    python_modules: tuple[TraceEvidence, ...]
    native_extensions: tuple[TraceEvidence, ...]
    loaded_libraries: tuple[TraceEvidence, ...]
    qt_plugins: tuple[TraceEvidence, ...]
    event_counts: tuple[tuple[str, int], ...]
    error: str | None = None
```

Vorgeschlagene zentrale Schema-ID: `zerorod-analysis/runtime-trace/v1`. Sie wird in Phase 1 genau
einmal unter `src/zerorod_analysis/runtime/schema.py` definiert. Zeitstempel sind UTC/ISO 8601;
Ausgabelisten und Quellen werden stabil sortiert. Wiederholte identische Beobachtungen erhöhen den
Zähler, statt Duplikate zu erzeugen.

`observed` bedeutet direkte Prozess-, Audit-, dyld- oder Qt-Beobachtung. `inferred` bezeichnet
statische Hinweise wie `otool` oder PyInstaller-XRef. `unresolved` bewahrt ein reales Ereignis, das
nicht sicher einer Bundle-Komponente zugeordnet werden konnte. Ein nicht-null Exit, Timeout,
Parserfehler oder fehlende Endsequenz setzt `incomplete`; vorhandene Beobachtungen bleiben erhalten.

Persistiert werden bevorzugt Pfade relativ zur `.app`-Wurzel. Systemkomponenten erhalten eine
stabile Systemidentität; andere absolute Benutzerpfade werden redigiert oder gehasht, nicht als
Klartext gespeichert.

## 8. Teststrategie für Phase 1

### Unit- und Contract-Tests

1. **Schema:** Pflichtfelder, Enum-Werte, zentrale Schema-ID und Build-ID aus
   `build_metadata.py`.
2. **Python-Import:** Subprozess importiert ein kleines Fixture-Modul; Audit und Snapshot ergeben
   `observed` mit korrektem Zähler.
3. **Dynamischer Import:** Fixture nutzt `importlib.import_module()` mit berechnetem Namen; das
   Ereignis muss trotz fehlendem statischem AST-Beleg erscheinen.
4. **Native Extension:** Standardbibliotheks-Extension wie `_json` oder `_sqlite3` in einem
   isolierten Subprozess; Test prüft Klassifikation, nicht einen maschinenspezifischen Pfad.
5. **Timeout:** Fixture wartet kontrolliert auf ein Event; Controller beendet nach großzügigem,
   testkonfigurierbarem Timeout, setzt `timed_out`/`incomplete` und hinterlässt keine Prozesse.
6. **Fehlstart:** nicht vorhandenes beziehungsweise nicht ausführbares Fixture liefert
   kontrollierten Fehler, non-zero Tool-Exit und optionalen Fehlertext.
7. **JSON:** zweimalige Serialisierung desselben Modells ist bytegleich, UTF-8 und gültiges JSON.
8. **Pfadnormalisierung:** Bundle-Pfade werden relativ; Home-/Temp-Pfade erscheinen nicht im
   gespeicherten Payload.
9. **Merge:** `observed` hat bei gleicher Identität Vorrang vor `inferred`; nicht zuordenbare
   Ereignisse bleiben `unresolved`; Zähler werden addiert.
10. **Qt:** versionierte, kleine Textfixtures mit Erfolgs-, Ablehnungs- und Fehlerzeilen aus
    `QT_DEBUG_PLUGINS`; Parser bleibt tolerant gegenüber unbekannten Zeilen. Ein echter Qt/macOS-
    Integrationstest wird separat markiert und darf die Core-Tests nicht von PySide6 abhängig
    machen.
11. **dyld:** gespeicherte Ausgabefixtures prüfen Dylib-/Framework-Erkennung und Redaction; keine
    Annahme einer bestimmten Systembibliotheksliste.

### Integrations- und Architekturtests

12. Kopie beziehungsweise Hash-/Metadatenmanifest eines minimalen `.app`-Fixtures vor und nach dem
    Trace vergleichen: keine Bundle-Datei geändert, hinzugefügt oder entfernt.
13. Ausgabe ausschließlich im expliziten Temp-/Zielverzeichnis; Abbruchpfade räumen temporäre
    Rohdaten in `finally` auf.
14. Source-Probe und minimaler Frozen-App-Smoke prüfen normalen Exit sowie unvollständigen Trace.
15. `startup-test`, Preview-Probe und Export-Probe werden getrennt getestet, damit lazy Imports
    tatsächlich ausgelöst werden.
16. Build-020-Public-API, Pipeline-, Report-, Compatibility- und bestehende Tests bleiben
    unverändert erfolgreich.
17. AST-Architekturtest: `zerorod_analysis` importiert weder PySide6 noch
    `zerorodcad_desktop`; macOS-Prozesscode bleibt unter `tools`/`packaging`.
18. Trace deaktiviert: Umgebung ohne Trace-Schalter erzeugt keine Trace-Datei und der bestehende
    Runtime-Hook setzt weiterhin nur den Qt-Plug-in-Pfad.

Es werden keine engen Laufzeitgrenzen wie `duration < 0.1` verwendet. Timeout-Tests synchronisieren
über Prozessausgabe oder eine Fixture-Datei und prüfen Zustandsübergänge statt Hardwaretempo.

## 9. Sicherheits- und Read-only-Konzept

- Bundle-Pfad vor Start auf `.app`, Executable und Ausführbarkeit validieren und anschließend nur
  lesend verwenden.
- Trace-Ziel muss explizit angegeben werden, darf nicht innerhalb des Bundles liegen und wird wie
  bei der ReportEngine gegen Path Traversal geprüft.
- Hook-Rohdaten zunächst in einem vom Controller erzeugten temporären Verzeichnis außerhalb des
  Bundles schreiben; erst nach erfolgreicher Normalisierung atomar ins Ziel ersetzen.
- Kindprozess mit eigener Prozessgruppe starten. Bei Timeout zuerst regulär terminieren, eine kurze
  Schonfrist abwarten und nur dann hart beenden; Exit und Unvollständigkeit immer festhalten.
- Cleanup in `finally`; eine fehlende oder beschädigte Hook-Datei darf dyld-/Qt-Belege nicht
  vernichten, sondern markiert den Trace als unvollständig.
- Trace-Umgebungsvariablen nur an den Kindprozess geben. Keine dauerhafte Änderung von Shell,
  Bundle, Plist, Signatur, Quarantine-Attributen oder Qt-Konfiguration.
- App-Logs und Home-basierte Einstellungen in Tests durch ein temporäres Home isolieren. Für reale
  Runs dokumentieren, dass die Anwendung ihr bestehendes Log außerhalb des Bundles schreiben kann.
- Vor/nach Tests ein deterministisches Bundle-Manifest aus relativen Pfaden, Größen und Hashes
  vergleichen. Keine automatische Reparatur oder Entfernung.
- Absolute Pfade früh normalisieren; rohe stderr-/Auditdaten nach erfolgreicher Verarbeitung
  entfernen, sofern der Benutzer sie nicht ausdrücklich als Diagnoseartefakt anfordert.

## 10. Konkrete Dateiänderungen für Phase 1

Vorgeschlagener Scope; noch nicht implementiert:

- `src/zerorod_analysis/runtime/__init__.py`
- `src/zerorod_analysis/runtime/models.py`
- `src/zerorod_analysis/runtime/schema.py`
- `src/zerorod_analysis/runtime/normalize.py`
- `src/zerorod_analysis/runtime/merge.py`
- `src/zerorod_analysis/runtime/serialization.py`
- `tools/trace_runtime.py`
- `tools/trace_runtime_imports.py` – auf gemeinsame Implementierung umstellen/Compatibility
- `packaging/macos/runtime_hook.py` – opt-in Recorder in vorhandenen Hook integrieren
- `scripts/validate-build021-m1.sh`
- `tests/test_runtime_trace_models.py`
- `tests/test_runtime_trace_imports.py`
- `tests/test_runtime_trace_native.py`
- `tests/test_runtime_trace_tool.py`
- `tests/test_runtime_trace_safety.py`
- `tests/test_runtime_trace_qt.py`
- `tests/test_runtime_trace_architecture.py`
- kleine Textfixtures unter `tests/fixtures/runtime_trace/`
- Architektur-, Schema-, Sicherheits-, Migrations- und ADR-Dokumentation für Build 021 M1

Nicht vorgesehen sind Änderungen an Pipeline-Reihenfolge, Reportrenderern, Confidence-, Risk- oder
Health-Regeln, Desktop-GUI und Top-Level-`zerorod_analysis.__all__`.

## 11. Risiken

- Audit-Hooks sehen keine Ereignisse vor ihrer Installation und nicht jeden nativen Loaderpfad.
- `DYLD_PRINT_LIBRARIES` kann bei signierten/hardened Prozessen anders wirken; dies muss an einem
  tatsächlichen Build geprüft werden.
- Qt-Diagnoseausgabe ist nicht als stabiles maschinenlesbares Protokoll garantiert.
- Startup-, Preview- und Export-Traces sind nur so vollständig wie die ausgeführten Workflows.
- Ein Timeout kann einen fachlich laufenden, aber auf Interaktion wartenden Prozess beenden; der
  Trace muss deshalb sichtbar `incomplete` sein.
- Native Bibliotheken können über Symlinks, Frameworkversionen oder Loader-Pfade mehrfach benannt
  werden; zu aggressive Zusammenführung wäre ein False-Negative-Risiko.
- Audit-/Qt-/dyld-Ausgaben können private absolute Pfade enthalten.
- `atexit`-basierte Endausgabe geht bei Crash oder SIGKILL verloren; inkrementelle Rohdaten oder
  Controller-Fallbacks sind nötig.
- Die Packaging-Spec-/Dokumentationsabweichung zu CasADi kann Trace-Erwartungen verfälschen.
- Runtime-Beobachtung beweist Nutzung im ausgeführten Szenario, fehlende Beobachtung beweist keine
  generelle Nichtnutzung.

## 12. Offene Entscheidungen

1. Welche Workflow-Profile sind verbindliches M1-Release-Gate: Startup, Preview und Export oder
   zusätzlich ein kontrollierter GUI-Ablauf?
2. Wird `DYLD_PRINT_LIBRARIES` auf den tatsächlich signierten/hardened Release-Bundles akzeptiert,
   oder ist `vmmap` als optionaler Fallback erforderlich?
3. Soll das Tool rohe Diagnoseausgabe auf ausdrücklichen Schalter aufbewahren dürfen, oder immer
   nur das normalisierte JSON?
4. Welche Schonfrist und welcher maximale Default-Timeout sind für interaktive App-Starts sinnvoll?
5. Wie werden Systempfade stabil benannt, ohne relevante Frameworkversionen zu verlieren?
6. Soll `tools/trace_runtime_imports.py` als dauerhaft unterstützter Compatibility-Aufruf bleiben
   oder nach einer dokumentierten Übergangsphase entfernt werden?
7. Muss der Preview-/Export-Workflow im gebündelten GUI-Prozess ausgelöst werden, oder gelten die
   vorhandenen headless Fachpfade als ausreichender Nachweis?
8. Die Zuordnung beobachteter Identitäten zu `LibraryUnit` und die Auswirkung auf Empfehlungen ist
   eine M2-Entscheidung; M1 sollte dafür nur verlustfreie, normalisierte Evidenz liefern.

## 13. Definition of Done für Build 021 M1

- Ein einziges versioniertes Runtime-Trace-Schema mit zentraler Build-ID ist implementiert und
  dokumentiert.
- Python-Importe, dynamische Imports, native Extension-Module, geladene Dylibs/Frameworks und
  Qt-Plug-ins können mit Quelle, Status und Zähler dargestellt werden.
- Der vorhandene PyInstaller-Runtime-Hook instrumentiert nur bei expliziter Aktivierung; normaler
  App-Start und Build-020-Public-API bleiben unverändert.
- Ein gemeinsamer Controller unterstützt Exit, Fehlstart, Timeout, kontrollierte Beendigung,
  unvollständige Traces und deterministisches JSON.
- Das analysierte Bundle, seine Signatur und Inhalte bleiben unverändert; Ausgaben liegen nur im
  expliziten externen Ziel.
- Absolute Benutzerpfade werden nicht dauerhaft gespeichert, wenn Bundle-relative oder redigierte
  Identitäten genügen.
- Das VTK-Spezialwerkzeug delegiert oder ist dokumentiert migriert; keine parallele Recorder-
  Implementierung bleibt bestehen.
- Unit-, Contract-, Sicherheits-, Architektur- und macOS-Smoke-Tests decken die in Abschnitt 8
  genannten Fälle ab.
- Keine PySide6- oder Desktop-Abhängigkeit gelangt in den Analysis Core.
- Alle Build-020-Tests sowie pytest, compileall, Ruff, Pre-Commit und das neue unverändernde
  Validierungsskript sind erfolgreich.
- M1 ändert noch keine fachliche Recommendation-, Risk- oder Health-Regel.

## 14. Empfohlene Commit-Nachricht für Phase 1

```text
feat(runtime): add read-only runtime trace foundation
```

## Discovery-Nachweise

Die Feststellungen basieren auf Branch-/Status-/Commit- und Python-Abfragen, der Suche nach
`AGENTS.md`/`AGENTS.override.md`, einer Repositorysuche nach Runtime-/Loader-Begriffen sowie der
direkten Prüfung der genannten Source-, Tool-, Script-, Packaging-, Test-, Dokumentations- und
ADR-Dateien. Phase 0 verändert ausschließlich dieses Dokument und erstellt keinen Commit.
