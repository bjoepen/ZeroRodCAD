# ZeroRodCAD Build 019.1a

## Stabilisierung & Repository Integration

Build 019.1a stabilisiert Scanner 2.0 und integriert ihn verbindlich in den Entwicklungsablauf des ZeroRodCAD-Repositories.

---

## 1. Wo arbeiten wir: Bash oder Environment?

Die Begriffe bezeichnen zwei unterschiedliche Ebenen:

| Kennzeichnung | Bedeutung | Beispiel |
|---|---|---|
| **BASH** | Befehle werden im macOS-Terminal im Repository-Verzeichnis eingegeben. | `git status`, `source .venv/bin/activate` |
| **ENVIRONMENT** | Eine aktivierte virtuelle Python-Umgebung innerhalb derselben Bash-Sitzung. | `python -m pytest`, `python -m ruff check .` |

Wichtig: **Das Environment ist kein zweites Fenster.** Es wird in Bash aktiviert. Nach der Aktivierung erscheint typischerweise `(.venv)` vor dem Prompt.

Beispiel:

```text
(.venv) bernd@Mac-mini ZeroRodCAD-App %
```

Alle folgenden Abschnitte sind deshalb ausdrücklich mit **BASH** oder **ENVIRONMENT** markiert.

---

## 2. Build in das Repository übernehmen

### BASH – Repository-Root öffnen

```bash
cd /Users/bernd/Projekte/ZeroRodCAD-App
```

Kontrolle:

```bash
pwd
git status
```

### BASH – Paket entpacken und übernehmen

```bash
unzip ~/Downloads/ZeroRodCAD-Build019.1a-Stabilisierung-Repository-Integration-Final.zip \
  -d /tmp/build0191a

rsync -av \
  /tmp/build0191a/ZeroRodCAD-Build019.1a-Stabilisierung-Repository-Integration-Final/ \
  ./
```

Danach prüfen:

```bash
git status
git diff --stat
git diff
```

---

## 3. Python-Environment einmalig einrichten

### BASH – automatischer Bootstrap

Der Bootstrap erzeugt `.venv`, installiert die Entwicklungswerkzeuge und richtet Pre-Commit ein:

```bash
bash scripts/bootstrap-dev.sh
```

Der Vorgang installiert lokal im Repository:

- pytest
- Ruff
- pre-commit

Es werden keine Pakete global in Homebrew-Python installiert.

### BASH – Environment in späteren Sitzungen aktivieren

Nach jedem neuen Terminalstart:

```bash
cd /Users/bernd/Projekte/ZeroRodCAD-App
source .venv/bin/activate
```

Kontrolle:

```bash
which python
python --version
python -m pytest --version
python -m ruff --version
pre-commit --version
```

`which python` muss auf einen Pfad innerhalb des Repositories zeigen, beispielsweise:

```text
/Users/bernd/Projekte/ZeroRodCAD-App/.venv/bin/python
```

Ab hier befinden wir uns im **ENVIRONMENT**.

---

## 4. Scanner ausführen

### ENVIRONMENT – empfohlener direkter Aufruf

```bash
python tools/scan_bundle.py "dist/ZeroRodCAD Desktop.app"
```

Dieser Aufruf war in Build 019.1 fehlerhaft und ist in Build 019.1a ausdrücklich abgesichert.

### ENVIRONMENT – gleichwertiger Modulaufruf

```bash
python -m tools.scan_bundle "dist/ZeroRodCAD Desktop.app"
```

Beide Varianten müssen dasselbe Ergebnis liefern.

### ENVIRONMENT – ausführliche Ausgabe

```bash
python tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --verbose
```

### ENVIRONMENT – ohne Cache

```bash
python tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --no-cache
```

### ENVIRONMENT – nur Mach-O-Dateien

```bash
python tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --macho-only
```

### ENVIRONMENT – nur bestimmte Dateiendungen

```bash
python tools/scan_bundle.py \
  "dist/ZeroRodCAD Desktop.app" \
  --extensions dylib so
```

### ENVIRONMENT – Version prüfen

```bash
python tools/scan_bundle.py --version
```

Erwartet:

```text
scan_bundle.py 019.1a
```

---

## 5. Ausgabedateien

Standardmäßig entstehen:

```text
build/reports/build-019.1-scanner2/
├── scanner2-report.md
└── scanner2-inventory.json
```

Der Cache liegt unter:

```text
.cache/bundle-analyzer/scanner2-cache.json
```

Das Cache-Schema trägt jetzt Version 2. Ein Cache aus Build 019.1 wird automatisch ignoriert und neu aufgebaut. Das ist beabsichtigt.

---

## 6. Tests und Qualitätsprüfung

### ENVIRONMENT – gezielte Tests

```bash
python -m pytest \
  tests/test_scanner2.py \
  tests/test_scanner2_classification.py \
  tests/test_scan_bundle_cli.py
```

### ENVIRONMENT – vollständige Build-Validierung

```bash
bash scripts/validate-build0191a.sh
```

Dieses Skript führt aus:

1. pytest
2. compileall
3. Ruff Check
4. Ruff Format Check
5. sämtliche Pre-Commit-Hooks

Falls die Meldung erscheint, dass kein Environment aktiv ist:

```bash
source .venv/bin/activate
bash scripts/validate-build0191a.sh
```

---

## 7. Erwarteter Scanner-Test

Erster Lauf:

```text
Cache: 0 Treffer, 1349 neu
```

Zweiter unveränderter Lauf:

```text
Cache: 1349 Treffer, 0 neu
```

Die konkreten Zahlen hängen vom aktuellen Bundle ab. Entscheidend ist, dass der zweite Lauf überwiegend oder vollständig aus Cache-Treffern besteht.

---

## 8. Git-Workflow und Commit

### BASH oder ENVIRONMENT

Git funktioniert in beiden Zuständen. Das aktivierte Environment kann bestehen bleiben.

Vor dem Commit:

```bash
git status
git diff --check
git diff --stat
```

Dateien vormerken:

```bash
git add \
  tools/__init__.py \
  tools/scan_bundle.py \
  tools/bundle_analyzer/__init__.py \
  tools/bundle_analyzer/scanner2 \
  tests/test_scanner2.py \
  tests/test_scanner2_classification.py \
  tests/test_scan_bundle_cli.py \
  scripts/bootstrap-dev.sh \
  scripts/validate-build0191a.sh \
  requirements-dev-build0191a.txt \
  docs/BUILD-019.1a-ANLEITUNG.md \
  docs/BUILD-019.1a-CHANGELOG.md
```

Commit:

```bash
git commit -m "build(019.1a): stabilize scanner and repository integration"
```

Sollten Pre-Commit-Hooks Dateien korrigieren, ist der Commit-Abbruch normal:

```bash
git add .
git commit -m "build(019.1a): stabilize scanner and repository integration"
```

Push:

```bash
git push
```

---

## 9. Abnahmekriterien

Build 019.1a ist abgeschlossen, wenn:

- direkter Skriptaufruf funktioniert
- Modulaufruf funktioniert
- `.venv` eingerichtet und aktiviert ist
- pytest, Ruff und pre-commit im Environment verfügbar sind
- erster Bundle-Scan erfolgreich ist
- zweiter Scan Cache-Treffer liefert
- alle Tests bestehen
- Pre-Commit erfolgreich ist
- Commit und Push durchgeführt wurden

---

## 10. Sicherheitsgrenze

Build 019.1a analysiert ausschließlich. Er entfernt, verschiebt oder verändert keine Bundle-Datei. Die eigentliche Mach-O-Abhängigkeitsanalyse folgt erst in Build 019.2.
