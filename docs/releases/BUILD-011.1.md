# Build 011.1 – Quality Gate

## Objective

Resolve the static-analysis findings from Build 011 and make the same checks automatic before future commits.

## Changes

- Modern return annotation without quotes.
- `zip(..., strict=True)` for related sequences.
- `Iterable` imported from `collections.abc`.
- Pre-commit hooks for Ruff and repository hygiene.

## Definition of Done

- [x] Four reported Ruff findings corrected.
- [x] Pre-commit configuration included.
- [x] Package version updated to 0.11.1.
- [x] Upgrade instructions included.
- [x] Python syntax validation completed.
- [ ] `ruff check .` executed locally.
- [ ] `ruff format --check .` executed locally.
- [ ] `pytest -v` executed locally.
- [ ] `pre-commit run --all-files` executed locally.
- [ ] macOS GUI regression test completed.
