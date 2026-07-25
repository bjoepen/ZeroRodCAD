# Build 019.2.3 – Repository Polish

## Ziel

Dieses Drop-in vereinheitlicht die sichtbare Versionsausgabe des Scanner-CLI mit dem bereits validierten Stand von Build 019.2.

## Änderung

- `tools/scan_bundle.py` meldet nun durchgängig `Build 019.2`.
- Der Standard-Berichtsordner bleibt `build/reports/build-019.2/`.
- `tests/test_scan_bundle_cli.py` prüft die Versionsausgabe ausdrücklich auf `019.2`.

## Nicht geändert

- keine Änderungen an Geometrie, Export, Vorschau oder Projektformat
- keine Änderungen an der Mach-O-Analyse
- keine Änderungen an Abhängigkeiten oder virtuellen Umgebungen
- keine Änderungen am bestehenden Validierungsskript

## Abnahmekriterium

Beide Aufrufe müssen dieselbe Version ausgeben:

```bash
python tools/scan_bundle.py --version
python -m tools.scan_bundle --version
```

Erwartete Ausgabe:

```text
ZeroRodCAD Scanner 2.0 – Build 019.2
```
