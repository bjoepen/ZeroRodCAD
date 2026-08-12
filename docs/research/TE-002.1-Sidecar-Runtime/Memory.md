# TE-002.1 — Memory

RSS in KB, measured via `ps` on the deepest live process-tree descendant (see
`Benchmark-Method.md` for why that matters for onefile builds). Small sample size (4 checkpoints
per variant) — reported as measured, not over-interpreted into a trend claim beyond what four
points can actually support.

## Variant C — onefile, persistent

| Checkpoint | RSS (KB) |
|---|---|
| after request 1 | 326,544 |
| after request 5 | 326,928 |
| after request 10 | 327,120 |
| after request 20 | 327,392 |

Delta over 20 requests: +848 KB (~0.26%).

## Variant D — onedir, persistent

| Checkpoint | RSS (KB) |
|---|---|
| after request 1 | 325,248 |
| after request 5 | 325,744 |
| after request 10 | 326,016 |
| after request 20 | 326,384 |

Delta over 20 requests: +1,136 KB (~0.35%).

## Assessment

Both variants sit at essentially the same steady-state working set (~318–320 MB — dominated by
`numpy`/`numba`/`scipy`/OCP, not by anything TE-002.1-specific) and both show a small, gradual
growth across 20 requests, on the same order of magnitude in both variants. Four checkpoints
across 20 requests is not enough data to distinguish "a real, slow, unbounded leak" from "a small
one-time steady-state settling effect (JIT caches, `numba` compilation caches, allocator
high-water-mark behavior)" — this would need many more requests over a much longer session to
answer with confidence, which was out of scope here. What the data does support: neither variant
shows an *alarming* or *runaway* growth pattern in the range actually measured, and the two
variants don't differ from each other in any way that would favor one packaging mode over the
other on memory grounds alone.

## One-shot variants (A, B) — for contrast, not directly comparable

One-shot processes exit after every request, so there is no persistent working set to track; each
request starts from the same ~1.5 MB (onefile bootloader, pre-work) or ~40 MB (onedir, pre-work)
snapshot and is torn down completely afterward. This is the structural memory trade-off against
the persistent variants: one-shot guarantees no cross-request memory carryover at the cost of
re-paying process startup every time; persistent avoids repeated startup cost at the cost of a
long-lived ~320 MB process that needs its own lifecycle management (see `Process-Lifecycle.md`).
