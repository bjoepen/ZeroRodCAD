# Build 019.2.4 – Ruff Formatting Fix

## Zweck

Dieser Korrektur-Drop-in behebt ausschließlich die von `ruff format --check` gemeldete Formatabweichung in `tools/scan_bundle.py`.

## Änderung

- `tools/scan_bundle.py` wird in die von Ruff erwartete Formatierung gebracht.
- Keine Logikänderung.
- Keine Änderung an Tests, Abhängigkeiten oder Berichtsformaten.

## Erwartetes Ergebnis

Nach dem Einspielen muss `bash scripts/validate-build0192.sh` vollständig durchlaufen und mit folgender Meldung enden:

```text
Build 019.2 validation passed.
```
