# Build 019.1a – Changelog

## Stabilisierung

- direkter Aufruf `python tools/scan_bundle.py …` funktioniert aus dem Repository-Root
- Modulaufruf `python -m tools.scan_bundle …` bleibt unterstützt
- fehlende Paketmarker für `tools` und `tools.bundle_analyzer` ergänzt
- kontrollierte CLI-Fehlerausgabe mit Exit-Code `2`
- Optionen `--verbose`, `--quiet` und `--version` ergänzt
- Report-Funktion liefert die erzeugten Dateipfade zurück
- Cache-Schema auf Version 2 angehoben; inkompatible Alt-Caches werden automatisch verworfen

## Repository-Integration

- Entwicklungsabhängigkeiten in `requirements-dev-build0191a.txt`
- Bash-Bootstrap für `.venv` in `scripts/bootstrap-dev.sh`
- vollständige Validierung in `scripts/validate-build0191a.sh`
- CLI-Regressionstests für direkten und modularen Start
- Anleitung unterscheidet ausdrücklich zwischen **Bash** und **Python Environment**

## Sicherheit

Der Scanner bleibt vollständig lesend. Weder das App-Bundle noch seine Mach-O-Dateien werden verändert.
