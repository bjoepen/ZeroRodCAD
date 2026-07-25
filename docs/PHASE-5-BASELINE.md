# Phase 5 – Baseline

Quelle: Bundle-Auswertung des aktuellen ZeroRodCAD-Desktop-Bundles.

| Kennzahl | Wert |
|---|---:|
| Native Dateien | 902 |
| Physische Gesamtgröße | 1,80 GiB |
| Eindeutiger Inhalt | 620,19 MiB |
| Byteidentische Mehrfachkopien | 1,20 GiB |
| Frameworks-root | 396 Dateien / 706,12 MiB |
| Resources | 295 Dateien / 614,89 MiB |
| VTK `__dot__dylibs` | 211 Dateien / 522,94 MiB |

## Kernergebnis

`Resources` ist vollständig eine Teilmenge der nativen Inhalte aus `Frameworks-root`.
`VTK-__dot__dylibs` ist vollständig eine Teilmenge von `Resources` und `Frameworks-root`.

Das belegt erhebliche physische Redundanz, gibt aber noch keinen Pfad automatisch zum Löschen frei.
