# `.zerorod` Project Format

A `.zerorod` file is JSON with an explicit format and version.

```json
{
  "format": "ZeroRodCAD Project",
  "version": 1,
  "parameters": {
    "project_name": "CBG Open G",
    "body_width": 38.0,
    "body_depth": 9.0
  }
}
```

Unknown parameters are rejected to avoid silently ignoring spelling mistakes or incompatible future fields.
