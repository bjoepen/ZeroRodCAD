# Build 019.2.1 – Drop-in-Fix für Entwicklungsabhängigkeiten

## Zweck

Dieser Drop-in behebt ausschließlich die unvollständige lokale Entwicklungsumgebung von Build 019.2. Bei der vollständigen Testsammlung wurden `tests/test_preview_contract.py` und `tests/test_startup.py` bereits während der Test-Erfassung abgebrochen, weil `PySide6` nicht installiert war.

```text
ModuleNotFoundError: No module named 'PySide6'
```

Die Mach-O-Implementierung und das bestehende Validierungsskript werden nicht umgebaut. Das vorhandene Repository bleibt die maßgebliche Basis.

## Enthaltene Änderungen

- `requirements-dev-build0192.txt`
  - ergänzt PySide6 für Desktop- und Startup-Tests;
  - enthält die für das Release-Gate benötigten Entwicklungswerkzeuge.
- `scripts/bootstrap-dev-build0192.sh`
  - erstellt oder verwendet `.venv`;
  - installiert die Build-019.2-Entwicklungsabhängigkeiten;
  - installiert die vorhandenen Pre-Commit-Hooks.

## Bewusste Begrenzung

CadQuery wird durch diesen gezielten Fix nicht erzwungen. Fehlt CadQuery, bleiben die vorhandenen Geometrie- und Vorschautests entsprechend ihrer bisherigen `pytest.importorskip`-Logik übersprungen. Das ist kein Fehler dieses Drop-ins.

## Erwartetes Ergebnis

Nach der Installation darf die Test-Erfassung nicht mehr wegen fehlendem PySide6 abbrechen. Anschließend läuft weiterhin das unveränderte Release-Gate:

```bash
bash scripts/validate-build0192.sh
```
