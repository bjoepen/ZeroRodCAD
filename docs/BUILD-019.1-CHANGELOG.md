# Build 019.1 – Änderungen

- vollständiger Scan aller Dateien und symbolischen Links in `Contents`
- persistenter Hash- und Metadaten-Cache
- SHA-256-Fingerprints mit Größe, Änderungszeit, Inode und Device
- Mach-O-Erkennung über Dateisignatur
- optionale Architekturermittlung über `lipo`
- automatische Klassifikation für VTK, OCP, PySide6, Qt, casadi und Bundle-Bereiche
- Pfad-, Hash-, Endungs- und Bereichsindizes
- Statistikmodell für Dateizahl, Größe, Symlinks, Mach-O und Python
- Filter für Bereiche, Endungen, Pfadmuster und Mach-O-Dateien
- Markdown- und JSON-Ausgabe
- Unit-Tests für Scan, Cache, Filter, Indizes und Klassifikation
