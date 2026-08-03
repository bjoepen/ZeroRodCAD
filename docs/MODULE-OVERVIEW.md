# Analysis Module Overview

| Module | Responsibility |
|---|---|
| `api.py` | Four stable public entry points |
| `models.py` | Legacy deduplication domain models |
| `exceptions.py` | Analysis exception base |
| `scanner/` | Scanner 2.0, cache, classification, filters, and legacy scanner |
| `macho/` | Mach-O inspection and dependency graph construction |
| `dependency/` | Internal dependency-graph facade |
| `deadlibs/` | Library aggregation, evidence resolution, and findings |
| `advisor/` | Internal risk and bundle-health facade |
| `report/` | Report-generation facilities |
| `optimization/` | Duplicate detection and non-destructive planning |

The source of truth is exclusively `src/zerorod_analysis`. Files below
`tools/bundle_analyzer` are backward-compatible import adapters.
