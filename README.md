# ZeroRodCAD Desktop – Build 018 / Phase 5 – Final Corrected

Dieses Paket startet Phase 5 der macOS-Bundle-Optimierung.

## Inhalt

- versionierter Bundle Analyzer
- SHA256-Duplikaterkennung
- Mach-O-Abhängigkeitsprüfung über `otool`
- nicht-destruktiver Deduplizierungsplan
- ECR
- Baseline
- Workflow
- Tests

## Ausführung

```bash
python3 -m tools.bundle_analyzer \
  "dist/ZeroRodCAD Desktop.app" \
  --plan
```

Danach:

```bash
open build/reports/phase5-bundle-deduplication/phase5-deduplication-plan.md
```

## Sicherheitsgrenze

Build 018 Phase 5.1 löscht und verändert keine Datei im App-Bundle.

## Commit-Vorschlag

```text
build(018): add phase 5 bundle deduplication analyzer
```

## Git-Befehle

```bash
git status
git add tools/bundle_analyzer tests docs README.md
git commit -m "build(018): add phase 5 bundle deduplication analyzer"
git push -u origin build-018-phase5-bundle-deduplication
```

## Korrekturstatus

Diese Datei ist die verbindliche, korrigierte Build-018-Auslieferung. Sie ersetzt die vorherige ZIP vollständig.
