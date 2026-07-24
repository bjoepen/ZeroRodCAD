# Contributing

## Branches

Use short-lived branches:

```text
feature/<topic>
fix/<topic>
build/<number>-<topic>
docs/<topic>
```

## Commit convention

```text
build(010): establish desktop foundation
feat(gui): add project editor
fix(engine): prevent channel and rod collision
docs(macos): clarify Python installation
test(engine): add tangent regression coverage
```

## Engineering change requests

Geometry changes must include:

- reason,
- old and new value,
- expected effect,
- validation method,
- prototype status.

## Pull requests

A pull request must state:

1. what changed,
2. why it changed,
3. how it was validated,
4. which risks remain.

Do not claim successful STL, STEP, slicer or physical validation unless it was actually performed.
