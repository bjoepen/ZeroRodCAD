# Build 019.3 – Milestone M4

## Bundle Optimization Advisor

M4 erweitert die Dead-Library-Analyse um eine erklärbare Entscheidungsebene.

### Neue Komponenten

- `RecommendationAdvisor`: erzeugt nachvollziehbare Empfehlungen und konkrete Aktionen.
- `RiskEvaluator`: bewertet das Entfernungsrisiko von 0 bis 100.
- `BundleHealthEvaluator`: verdichtet Findings zu einem Bundle-Health-Wert.
- `optimization-plan.md`: priorisierter Maßnahmenplan.
- JSON-Schema 2 mit `risk_score`, `risk_label`, `actions` und `bundle_health`.

### Priorisierung

Die Maßnahmenreihenfolge lautet:

1. SAFE REMOVE – geringstes Risiko zuerst, danach größtes Einsparpotenzial.
2. REVIEW – zuerst Laufzeit- und Manifestprüfung.
3. KEEP – dokumentiert, aber nicht zur Entfernung vorgeschlagen.

### Sicherheitsprinzip

Keine Empfehlung entfernt Dateien automatisch. SAFE REMOVE bleibt eine statische Empfehlung und erfordert immer einen reproduzierbaren Bundle-Test.
