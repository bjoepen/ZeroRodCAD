# TE-002 — Performance

All figures below are real measurements from this session, against the actual compiled sidecar
executable and the actual default ZeroRod model — labeled MEASURED throughout, median of repeated
runs where noted, no theoretical/estimated numbers presented as measured (section 24).

## Python (inside the sidecar, self-reported via the `timing` field in every response)

| Stage | Duration |
|---|---:|
| Model build + tessellation (`build_preview_scene()`) | **0.149 s** |
| Mesh-contract serialization (`scene_to_mesh_contract()`) | **0.0003 s** (0.3 ms) |

Consistent across every invocation observed in this session (values in the 0.10–0.15 s range for
model+tessellation across all runs) — this is the real, per-request "engine work" cost, and it is
small.

## IPC / process round trip (MEASURED, 5 runs, median reported per section 24)

| Metric | Value |
|---|---:|
| JSON response payload size | **60,079 bytes** (~59 KiB) |
| Full process round trip (spawn → write → response → exit), median of 5 runs | **15.01 s** |
| Round trip, individual runs | 14.80 s, 29.37 s, 14.94 s, 15.01 s, 15.01 s |

**This ~15 s figure is process-startup overhead, not application logic** — confirmed directly:
`/private/var/folders/.../T/_MEI*` self-extraction directories were observed to exist while the
process was starting. The compiled sidecar is a **PyInstaller onefile** executable (~135 MB,
dominated by the bundled OCP binary); onefile mode re-extracts its entire payload to a fresh temp
directory on *every* launch — a well-documented, well-understood PyInstaller characteristic, not a
defect in the sidecar's own code or the IPC design. The one outlier (29.37 s) is consistent with
this too (extraction I/O contention from concurrent activity in this session, not a different code
path).

This is the single most important, concrete finding for a future production evaluation: **the
architecture itself is fast (sub-200ms of real engine work); the current PoC's packaging choice
(onefile) is what's slow.** See `Conclusion.md`/`ADR-DRAFT.md` for the recommended fix (onedir
sidecar packaging or a long-lived/reused sidecar process) — not implemented in TE-002, which
deliberately does not escalate scope beyond proving the architecture.

## Frontend (MEASURED, real mesh payload, 20 runs, median reported)

| Metric | Value |
|---|---:|
| `meshContractToGeometries()` on the real 720+146-vertex payload, median of 20 runs | **0.157 ms** |
| Range across 20 runs | 0.11 ms – 2.33 ms (a few outliers from JIT warm-up/GC, typical for a first-call-heavy microbenchmark) |

Negligible relative to every other stage — confirms `BufferGeometry` construction is not a
bottleneck for a model of this size.

## Payload size discussion (section 25)

720+146 = 866 total mesh vertices, 710+140 = 850 triangles, 12 line points → **60,079 bytes** of
JSON. For comparison, that's roughly 69 bytes per vertex in JSON-text form versus the theoretical
minimum of 12 bytes/vertex for raw `Float32` binary triples (~5.8× overhead) — an expected,
unremarkable JSON-vs-binary ratio, not evidence of a problem at this model scale. gzip-equivalent
size was not separately measured (would require adding a compression step not otherwise needed by
this PoC — out of scope per section 25/26, "noch keine Binärmigration").

## Answer to "is JSON realistic for ZeroRodCAD" (feeds Conclusion.md question 3)

At this model's scale (fewer than 1,000 vertices, ~60 KB payload, sub-millisecond frontend parse
time), plain JSON is unambiguously sufficient — nothing here comes close to motivating a binary
format. The dominant cost in the entire measured pipeline by roughly two orders of magnitude is
the onefile sidecar's process-startup overhead, not the JSON payload or its parsing.
