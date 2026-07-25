# Build 019.3 – Milestone M3: Integration & Reporting

## Ziel

M3 verbindet die in M1 und M2 entwickelte Dead-Library-Engine mit dem bestehenden Scanner-2.0-CLI und erzeugt aus einem kanonischen Analysemodell reproduzierbare JSON- und Markdown-Berichte.

## Neue CLI-Option

```bash
python tools/scan_bundle.py /Pfad/Zu/ZeroRodCAD.app \
  --output-dir reports \
  --dead-libraries
```

Die Option `--dead-libraries` erstellt intern immer den Mach-O-Abhängigkeitsgraphen. Separate Mach-O-Berichte werden nur erzeugt, wenn zusätzlich `--macho-dependencies` gesetzt ist:

```bash
python tools/scan_bundle.py /Pfad/Zu/ZeroRodCAD.app \
  --output-dir reports \
  --dead-libraries \
  --macho-dependencies
```

## Erzeugte Dead-Library-Berichte

Unter `<output-dir>/dead-libraries/` entstehen:

- `dead-libraries.json` – kanonisches, maschinenlesbares Ergebnis
- `dead-libraries.md` – priorisierte Findings mit Konfidenz und Empfehlung
- `bundle-size-analysis.md` – Größen- und Einsparübersicht
- `optimization-report.md` – Arbeitsreihenfolge SAFE REMOVE / REVIEW / KEEP

Die Markdown-Berichte werden aus demselben Ergebnisobjekt wie das JSON erzeugt. Dadurch existiert nur eine fachliche Quelle der Wahrheit.

## Mach-O-Berichte

Mit `--macho-dependencies` werden zusätzlich geschrieben:

- `macho-dependencies.json`
- `macho-dependencies.md`
- `macho-dependencies.dot`
- `macho-unresolved.md`

## Sicherheitsgrenze

`SAFE REMOVE` ist eine statische Analyseempfehlung, keine automatische Löschfreigabe. Kandidaten müssen zunächst in einer Kopie des Bundles entfernt und anschließend durch einen reproduzierbaren Laufzeit- und Funktionscheck validiert werden.

## Validierung

```bash
bash scripts/validate-build0193-m3.sh
```

Das Skript prüft den vollständigen Testbestand, Bytecode-Kompilierung, Ruff und alle Pre-Commit-Hooks.
