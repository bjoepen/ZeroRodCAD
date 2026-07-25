# Build 019.3 – Milestone M1: Dead Library Engine Foundation

## Zweck

M1 führt das fachliche Fundament für die spätere Dead-Library-Analyse ein. Der Milestone arbeitet noch nicht direkt auf einem macOS-App-Bundle und besitzt noch keine CLI-Option. Er stellt stabile Datenmodelle, eine erste deterministische Auswertung und die Größenaggregation bereit.

## Neue Komponenten

- `deadlibs/models.py`: Bibliotheken, Referenzen, Usage Records, Findings und Resultate
- `deadlibs/confidence.py`: validierte technische Konfidenzstufen
- `deadlibs/resolver.py`: Zuordnung zu `SAFE REMOVE`, `REVIEW` und `KEEP`
- `deadlibs/size.py`: Größen- und Einsparungsübersicht
- `tests/test_deadlibs_foundation.py`: isolierte Tests des fachlichen Fundaments

## Bewusste Grenzen von M1

Noch nicht Bestandteil dieses Milestones:

- Mach-O-Dependency-Graph-Anbindung
- Python-Importanalyse
- Plugin- und Dynamic-Load-Auswertung
- CLI-Option `--dead-libraries`
- JSON- und Markdown-Reports
- automatische Entfernung von Dateien

M1 entfernt grundsätzlich keine Dateien. `SAFE REMOVE` ist zunächst nur eine modellierte Empfehlung für spätere Analyseergebnisse.

## Validierung

```bash
bash scripts/validate-build0193-m1.sh
```

Erwartete Abschlussmeldung:

```text
Build 019.3 Milestone M1 validation passed.
```
