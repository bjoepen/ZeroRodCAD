# TE-002 — Sidecar Contract (`zerorod-sidecar/v1`)

## Protocol

Plain JSON over stdin/stdout. No HTTP, no WebSocket, no gRPC (section 11) — the sidecar reads
**exactly one** newline-terminated JSON request line from stdin, writes **exactly one** JSON
response line to stdout, then exits.

This one-shot shape is not arbitrary: `@tauri-apps/plugin-shell`'s `Child.write()` cannot close a
sidecar's stdin (no EOF signal available — see `Discovery.md`), so a sidecar that tried to
`read()` to EOF would hang forever when driven from Tauri. Reading one line via
`sys.stdin.readline()` sidesteps this entirely.

## Request

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-1754630...",
  "command": "preview",
  "parameters": {}
}
```

- `schema` — must be exactly `"zerorod-sidecar/v1"`.
- `request_id` — caller-assigned, non-empty string, echoed back verbatim.
- `command` — currently only `"preview"` is implemented (default ZeroRod parameters only; a
  request with any non-empty `parameters` object is rejected with `unsupported_parameters` —
  parametrized models were out of scope for this PoC).
- `parameters` — object, may be empty.

## Response — success

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-1754630...",
  "ok": true,
  "result": { "...": "see Mesh-Contract.md" }
}
```

## Response — error

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-1754630...",
  "ok": false,
  "error": { "code": "unknown_command", "message": "unknown command: 'bogus'" }
}
```

Error codes actually implemented and tested (`tools/poc/tauri/sidecar/`,
`tests/poc/tauri/test_sidecar_main.py`):

| Code | Cause |
|---|---|
| `invalid_json` | stdin line was not parseable JSON |
| `invalid_schema` | `schema` field missing or wrong |
| `invalid_request` | `request_id`/`command`/`parameters` missing or wrong type |
| `unknown_command` | `command` is not `"preview"` |
| `unsupported_parameters` | non-empty `parameters` sent to `preview` (PoC scope limit) |
| `invalid_mesh` | the generated mesh failed the sidecar's own validation (should not happen with the real default model — defensive) |
| `internal_error` | any other exception; the *message* is `"{ExceptionType}: {str(exc)}"`, never a raw traceback |
| `empty_request` | stdin closed with no line ever received |

**No raw Python traceback is ever put in a response** (section 11's explicit requirement) —
verified by `test_preview_response_never_contains_traceback_text` (asserts neither `"Traceback"`
nor `File "` substrings appear in any serialized response). Full tracebacks are printed to stderr
only, for local debugging.

`stdout` never carries anything except the single response line — verified directly
(`test_sidecar_stdout_is_not_corrupted_by_stderr`, and manually: `wc -l` on captured stdout always
reports exactly 1).

## Rust-side parsing (`src-tauri/src/sidecar.rs::parse_response`)

The Rust command applies the identical set of checks independently before trusting the payload:
exactly one non-empty line, valid JSON, matching schema, matching `request_id`, `ok` truthy with a
`result` field (or a structured error surfaced to the frontend as `PreviewError { code, message }`).
10 unit tests cover this (`cargo test`, all passing) — see `Tauri-Architecture.md`.

## Mesh validation (section 13)

Both the sidecar (Python, `mesh_contract.py::validate_mesh_contract`) and the frontend (JS,
`mesh.js::validateMeshPayload`) independently re-check: schema id, non-empty meshes, positions
length divisible by 3, indices length divisible by 3, every index within the vertex range, no
NaN/Infinity anywhere in positions or bounds, and a well-formed `bounds.min`/`bounds.max`. An
invalid payload never reaches the renderer — `meshContractToGeometries()` throws before any
`THREE.BufferGeometry` is constructed from bad data.
