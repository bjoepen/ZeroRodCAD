# Phase 5 – Arbeitsablauf

## 1. Vorbereitung

```bash
git switch main
git pull --ff-only
git switch -c build-018-phase5-bundle-deduplication
```

## 2. Analyzer installieren

Das Verzeichnis `tools/bundle_analyzer` in das Repository übernehmen.

## 3. Tests

```bash
python3 -m pytest tests/test_duplicates.py tests/test_planner.py
```

## 4. Dry-Run

```bash
python3 -m tools.bundle_analyzer \
  "dist/ZeroRodCAD Desktop.app" \
  --plan
```

## 5. Bericht öffnen

```bash
open build/reports/phase5-bundle-deduplication/phase5-deduplication-plan.md
```

## 6. Phase 5.2

Als erste kontrollierte Testgruppe wird nicht sofort das 142-MiB-Modul gewählt. Stattdessen ist eine kleine, dreifach vorhandene Bibliothek vorzuziehen. Dadurch können Loader-Pfad, Codesigning und Laufzeittests mit geringerem Risiko verifiziert werden.

## Validierung

```text
[ ] App startet über Finder
[ ] App startet über Terminal
[ ] neues Projekt
[ ] bestehendes Projekt öffnen
[ ] 3D-Preview
[ ] STL-Export
[ ] STEP-Export
[ ] App schließen und erneut starten
[ ] codesign --verify --deep --strict
[ ] Bundle-Größe vor/nach Änderung
```
