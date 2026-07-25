# Build 019.3 – Milestone M2: Dead Library Engine Core

## Ziel

M2 erweitert die in M1 eingeführte Foundation zu einer nutzbaren Analyse-Engine. Der Milestone gruppiert Bundle-Dateien zu logischen Bibliotheken, sammelt Referenzsignale, bewertet das Risiko und berechnet das sichere Einsparpotenzial.

## Voraussetzungen

- M1 wurde vollständig angewendet und validiert.
- `pyproject.toml` enthält für Pytest `pythonpath = [".", "src"]`.
- Die virtuelle Umgebung ist aktiv.
- Die Entwicklungsabhängigkeiten aus Build 019.2 sind installiert.

## Neue bzw. ausgebaute Komponenten

### Mach-O Dependency Graph

`tools/bundle_analyzer/macho.py` enthält nun:

- `MachOBinary`
- `DependencyGraph`
- `MachOAnalyzer`
- `build_dependency_graph()`
- Auflösung von `@rpath`, `@loader_path` und `@executable_path`
- transitive Erreichbarkeitsanalyse über `reachable_from()`
- getrennte Erfassung externer beziehungsweise nicht auflösbarer Abhängigkeiten

### LibraryUnit-Aggregation

`deadlibs/aggregate.py` gruppiert:

- komplette `.framework`-Bundles,
- einzelne `.dylib`- und `.so`-Bibliotheken,
- Top-Level-Pakete unter `site-packages`.

Symbolische Links werden in der Pfadliste geführt, aber nicht erneut zur Größe addiert.

### Referenzauflösung

`resolve_usage()` sammelt:

- Mach-O-Abhängigkeiten aus dem zentralen `DependencyGraph`,
- statische Python-Imports mittels `ast`,
- dynamische Ladehinweise bei `importlib.import_module` und `dlopen`.

Die Engine führt keine eigenen `otool`-Aufrufe aus. Der Mach-O-Graph bleibt die einzige Quelle für native Abhängigkeiten.

### Confidence und Empfehlung

Technische Bewertung und Benutzerempfehlung bleiben getrennt:

| Situation | Confidence | Empfehlung |
|---|---|---|
| Statische Referenz vorhanden | HIGH | KEEP |
| Keine Referenz bei Framework/Dylib | HIGH | SAFE REMOVE |
| Python-Paket ohne Referenz | MEDIUM | REVIEW |
| Dynamischer oder nicht auflösbarer Hinweis | LOW | REVIEW |
| Redundante Kopie | HIGH | SAFE REMOVE |

### Größenanalyse

`compute_savings()` berücksichtigt ausschließlich Findings mit `SAFE REMOVE`. Die Ergebnisse werden absteigend nach möglicher Einsparung sortiert.

## Noch nicht Bestandteil von M2

Folgende Punkte bleiben ausdrücklich M3 vorbehalten:

- CLI-Option `--dead-libraries`,
- JSON- und Markdown-Reports,
- Plugin-Manifest-Auswertung über zusätzliche Dateiformate,
- End-to-End-Integration in `tools/scan_bundle.py`.

## Validierung

```bash
bash scripts/validate-build0193-m2.sh
```

Das Skript führt den vollständigen Repository-Testbestand, `compileall`, Ruff und – falls installiert – alle Pre-Commit-Hooks aus.
