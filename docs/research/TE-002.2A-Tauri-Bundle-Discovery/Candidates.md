# TE-002.2A — Candidates for TE-002.2B Investigation

Discovery only — sizes, roles, and runtime-evidence status, no removal decisions. Runtime evidence
is reused from TE-002.1's existing persistent-onedir trace (one real `preview` + `shutdown` round
trip, `build/reports/te0021-sidecar-runtime/runtime-trace/persistent-onedir-trace.json`), not
re-captured. Per the mandate governing this evaluation: **NOT OBSERVED does not mean unused** — a
single trace covers one request with default parameters, not every code path (exports, alternate
parameter combinations, error-handling branches).

## Evidence status legend

- **REQUIRED** — backed by concrete evidence of necessity (e.g. confirmed functionally essential
  in a prior TE).
- **OBSERVED** — appeared in the runtime trace during the real request that was captured.
- **NOT OBSERVED** — did not appear in that one trace; absence of evidence, not evidence of
  absence.
- **STRUCTURAL** — a packaging/runtime-infrastructure artifact, not a library-usage question.

## Candidates

### 1. llvmlite — `libllvmlite.dylib`
- Size: 122.78 MiB (single file, the second-largest in the bundle)
- Runtime evidence: **NOT OBSERVED** (0 hits in the traced request)
- Role: numba's LLVM-based JIT compilation backend
- Origin: transitive dependency of numba
- TE-002.2B candidate: **YES**

### 2. scipy
- Size: 31.75 MiB
- Runtime evidence: **NOT OBSERVED**
- Role: unclear from this trace alone — a large, general-purpose scientific library; which
  submodules (if any) CadQuery's geometry code actually calls was not investigated here
- Origin: CadQuery's own declared `requires_dist` (confirmed in TE-001's original dependency
  research)
- TE-002.2B candidate: **YES**

### 3. numba
- Size: 1.1 MiB (small itself, but structurally paired with llvmlite — see #1)
- Runtime evidence: **NOT OBSERVED**
- Role: JIT-compilation library; pulls in llvmlite as its own dependency
- TE-002.2B candidate: **YES** (investigate together with llvmlite — removing one without the
  other doesn't make sense if they're genuinely unused)

### 4. Duplicate onefile sidecar (`Contents/MacOS/zerorod-engine`)
- Size: 135.45 MiB
- Evidence status: **STRUCTURAL** — this is a packaging decision, not a code-usage question. It
  exists because TE-002.1 deliberately kept both the onefile fallback path
  (`requestPreviewOneShot`) and the onedir default path (`persistent_preview`) in the same test
  bundle for its own variant comparison.
- TE-002.2B candidate: **YES** — if Variant D (persistent + onedir) is finalized as the sole
  production strategy, this copy's presence is a packaging-config question (whether to keep
  `externalBin` wired up at all), not a dependency-removal question.

### 5. Duplicate dylibs within the onedir sidecar (77 hash-verified groups, 93.90 MiB reclaimable)
- Size: 93.90 MiB (dominated by 74 `TK*.dylib` OpenCASCADE files present both at `_internal/` root
  and under `_internal/OCP/.dylibs/`)
- Evidence status: **STRUCTURAL** — a PyInstaller dependency-collection artifact (the OCP wheel's
  own bundled `.dylibs/` convention vs. PyInstaller's separate top-level dylib collection), not a
  question of whether any library is used.
- TE-002.2B candidate: **YES** — a PyInstaller packaging/config investigation (e.g. whether
  `--exclude` or a custom hook can prevent the double-collection), explicitly not a dependency
  removal.

## Explicitly NOT candidates (for contrast — not omitted by oversight)

- **OCP** (216.18 MiB) — **REQUIRED**. The CAD kernel binding; confirmed functionally essential by
  every prior TE in this series (TE-001 through TE-002.1). Also flagged "SAFE REMOVE" by the dead-
  library analyzer — a known false positive already documented in TE-001.1/TE-001.2, not
  reconsidered here.
- **casadi** (8.98 MiB) — **OBSERVED** in the runtime trace (2 python_modules, 1 native extension).
- **nlopt** (1.2 MiB) — **OBSERVED** (3 python_modules, 1 native extension).
- **numpy** (6.55 MiB) — **OBSERVED** (87 python_modules, 2 native extensions) — foundational,
  used throughout.
- **ezdxf** (1.7 MiB) — **OBSERVED** (206 python_modules, 8 native extensions).
- **cadquery** itself — **OBSERVED** (28 python_modules).

## What TE-002.2B would need to do to move any candidate from PLAUSIBLE to CONFIRMED

Not performed here (out of scope, discovery-only): (1) capture additional runtime traces covering
export operations and non-default parameter combinations, to see whether scipy/numba/llvmlite get
exercised under conditions the single TE-002.1 trace didn't hit; (2) if still not observed across a
broader trace set, investigate *why* PyInstaller's static analysis included them (which import
statement in the dependency graph triggered their collection) before considering any exclude; (3)
for the duplicate-dylib finding, determine whether a PyInstaller hook/exclude can be safely applied
without breaking OCP's own dylib resolution at runtime. None of this was attempted in TE-002.2A.
