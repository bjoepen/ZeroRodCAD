# ECR-018-005 – macOS Bundle Deduplication

## Status

Freigegeben für Phase 5.1: nicht-destruktive Planung und Validierung.

## Ausgangslage

Die Bundle-Analyse ergab:

- 902 analysierte native Bibliotheken
- 1,80 GiB physische Gesamtgröße
- 620,19 MiB eindeutiger Inhalt
- 1,20 GiB theoretisch redundanter byteidentischer Inhalt
- 294 Bibliotheken identisch in `Frameworks` und `Resources`
- 211 Bibliotheken identisch in `Frameworks`, `Resources` und `vtkmodules/__dot__dylibs`

## Ziel

Die Mehrfachablage nativer Bibliotheken wird reproduzierbar untersucht und anschließend schrittweise reduziert, ohne Preview, STL, STEP, Projektdateien oder macOS-Startverhalten zu beschädigen.

## Umfang Phase 5.1

- Bundle Analyzer als versioniertes Entwicklerwerkzeug
- SHA256-basierte Duplikaterkennung
- Mach-O-ID- und Abhängigkeitsvergleich
- kanonische Zielpfadplanung
- ausschließlich Dry-Run
- Markdown- und JSON-Bericht
- keine automatische Dateientfernung

## Nicht enthalten

- pauschales Löschen von `Resources/*.dylib`
- pauschales Löschen von `__dot__dylibs`
- Änderung von `install_name`
- Änderung von `@rpath`
- Codesigning oder Notarisierung
- produktive Deduplizierung

## Risiken

- Python-Erweiterungen können relative Loader-Pfade erwarten.
- PyInstaller kann dieselbe Datei an mehreren Zielpfaden benötigen.
- Änderungen brechen eine vorhandene Codesignatur.
- Starttests allein reichen nicht; Preview und Export müssen separat validiert werden.

## Definition of Done – Phase 5.1

- [ ] Analyzer läuft auf dem aktuellen App-Bundle.
- [ ] Markdown- und JSON-Plan werden erzeugt.
- [ ] Keine Datei im Bundle wurde verändert.
- [ ] größte Duplikatgruppen sind dokumentiert.
- [ ] Mach-O-Abhängigkeiten wurden erfasst.
- [ ] Baseline-Größe ist dokumentiert.
- [ ] Phase-5.2-Testgruppe ist ausgewählt.
