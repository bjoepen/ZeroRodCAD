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
| `optimization/` | Duplicate detection and non-destructive planning |
| `pipeline/` | Ordered four-stage analysis orchestration |
| `report/` | Unified renderer registry and atomic report persistence |
| `metrics.py` | Data-only per-run pipeline, renderer, and benchmark metrics |
| `benchmark.py` | Internal benchmark orchestration |
| `build_metadata.py` | Single source of current build identity |

The source of truth is exclusively `src/zerorod_analysis`. Files below
`tools/bundle_analyzer` are backward-compatible import adapters.
