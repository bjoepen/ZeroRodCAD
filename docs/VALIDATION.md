# Validation

## Automated

```bash
pytest -v
```

Tests cover:

- centered string positions,
- variable string counts,
- tangent calculation,
- project file round-trip,
- parameter errors,
- one valid body solid,
- channel and rod non-intersection.

## Required local review

Before release:

1. Run all tests.
2. Export the example project.
3. Open the STEP assembly in a CAD viewer.
4. Import the STL into a slicer without automatic repair.
5. Inspect all channel layers.
6. Print a prototype.
7. Measure critical dimensions.
8. Document the result.

No release may claim physical validation until this process is complete.
