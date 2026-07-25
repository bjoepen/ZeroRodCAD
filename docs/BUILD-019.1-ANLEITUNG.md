# ZeroRodCAD Build 019.1 – Scanner 2.0

## Ziel

Build 019.1 ergänzt den Bundle Analyzer aus Build 018 um einen vollständigen,
nicht-destruktiven Bundle-Index. Der Scanner erfasst alle Dateien und Symlinks,
klassifiziert sie, erstellt Indizes und verwendet bei Wiederholungsläufen einen
persistenten Cache.

## Enthaltene Dateien

```text
tools/
├── scan_bundle.py
└── bundle_analyzer/
    └── scanner2/
        ├── __init__.py
        ├── cache.py
        ├── classification.py
        ├── database.py
        ├── filters.py
        ├── models.py
        ├── native.py
        ├── report.py
        └── scanner.py

tests/
├── test_scanner2.py
└── test_scanner2_classification.py
```

## Integration in das Repository

Der ZIP-Inhalt ist als Overlay für das bestehende Repository vorbereitet.
Im Projektverzeichnis ausführen:

```bash
unzip ~/Downloads/ZeroRodCAD-Build019.1-Scanner-2.0-Final.zip -d /tmp/build0191
rsync -av \
  /tmp/build0191/ZeroRodCAD-Build019.1-Scanner-2.0-Final/ \
  ./
```

Danach prüfen:

```bash
git status
git diff --stat
git diff
```

## Scanner ausführen

```bash
python3 tools/scan_bundle.py "dist/ZeroRodCAD Desktop.app"
```

Die Standardausgabe liegt unter:

```text
build/reports/build-019.1-scanner2/
├── scanner2-report.md
└── scanner2-inventory.json
```

Der Cache liegt standardmäßig unter:

```text
.cache/bundle-analyzer/scanner2-cache.json
```

## Filterbeispiele

Nur Mach-O-Dateien:

```bash
python3 tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --macho-only
```

Nur dylib-Dateien:

```bash
python3 tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --extensions dylib
```

Nur der Bereich VTK:

```bash
python3 tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --include-section VTK
```

Cache für einen Kontrolllauf deaktivieren:

```bash
python3 tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --no-cache
```

## Validierung

Die Projektumgebung aktivieren und ausführen:

```bash
python3 -m pytest tests/test_scanner2.py \
  tests/test_scanner2_classification.py
python3 -m compileall tools tests
pre-commit run --all-files
```

Ruff kann auch über die Projektumgebung gestartet werden:

```bash
python3 -m ruff check .
python3 -m ruff format --check .
```

Ist Ruff nicht global installiert, bleibt `pre-commit run --all-files` die
maßgebliche Prüfung, da Pre-Commit seine eigene isolierte Ruff-Umgebung nutzt.

## Commit und Push

```bash
git add tools/scan_bundle.py \
  tools/bundle_analyzer/scanner2 \
  tests/test_scanner2.py \
  tests/test_scanner2_classification.py

git commit -m "build(019.1): implement scanner 2.0 bundle index and cache"
git push
```

## Sicherheitsgrenze

Scanner 2.0 liest das App-Bundle ausschließlich. Er entfernt, verschiebt oder
verändert keine Bundle-Dateien und führt keine Codesignatur aus.
