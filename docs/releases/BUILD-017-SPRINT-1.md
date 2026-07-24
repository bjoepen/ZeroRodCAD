# Build 017 – Sprint 1

## Repository Cleanup and Git Hygiene

Sprint 1 removes generated local files from the repository and introduces a
clear documentation structure.

## Removed

- macOS archive metadata (`__MACOSX`, AppleDouble files),
- Python bytecode caches,
- generated `*.egg-info` metadata,
- generated export directory.

## Added

- comprehensive `.gitignore`,
- consistent `.gitattributes`,
- documentation index,
- dedicated documentation groups for guides, references, releases and upgrades.

## Preserved

- source code,
- tests,
- macOS packaging specifications,
- example project,
- application assets,
- historical release and upgrade documentation.

## Validation

Run after replacing the repository contents:

```bash
source .venv/bin/activate
pre-commit run --all-files
pytest -v
```

Generated metadata may reappear locally after installation, but Git now ignores
it automatically.
