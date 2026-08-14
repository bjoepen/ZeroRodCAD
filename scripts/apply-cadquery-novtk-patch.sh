#!/usr/bin/env bash
# Build 026 M1 — deterministic, repository-tracked application of the TE-001.1
# CadQuery No-VTK import-decoupling patch (docs/research/TE-001.1-CadQuery-NoVTK/patches/).
#
# Replaces the previous mechanism, which copied 4 already-patched files out of
# a separate, undocumented, hand-patched local venv (.venv-novtk-poc) with no
# tracked provenance. This script instead applies the tracked unified diffs
# directly to a target venv's freshly pip-installed cadquery==2.8.0 — no
# dependency on any other local venv's state.
#
# Usage: scripts/apply-cadquery-novtk-patch.sh <path-to-venv-python>
set -euo pipefail

cd "$(dirname "$0")/.."

TARGET_PYTHON="${1:?usage: apply-cadquery-novtk-patch.sh <path-to-venv-python>}"
PATCH_DIR="docs/research/TE-001.1-CadQuery-NoVTK/patches"

if [ ! -x "${TARGET_PYTHON}" ]; then
  echo "target python interpreter not found or not executable: ${TARGET_PYTHON}" >&2
  exit 1
fi

# Locate the installed cadquery package directory WITHOUT importing it —
# unpatched upstream cadquery fails on `import cadquery` in a No-VTK
# environment (that's the exact defect this patch fixes), so `import
# cadquery, os; ...` cannot be used here before patching.
CADQUERY_LOCATION="$("${TARGET_PYTHON}" -m pip show cadquery 2>/dev/null | awk -F': ' '/^Location:/ {print $2}')"
if [ -z "${CADQUERY_LOCATION}" ]; then
  echo "cadquery is not installed in the target environment (pip show cadquery found nothing)" >&2
  exit 1
fi
CADQUERY_DIR="${CADQUERY_LOCATION}/cadquery"
echo "== apply-cadquery-novtk-patch: target cadquery install: ${CADQUERY_DIR} =="

# File-to-patch mapping, in application order.
FILES=(
  "occ_impl/shapes.py"
  "occ_impl/exporters/vtk.py"
  "occ_impl/assembly.py"
  "occ_impl/exporters/assembly.py"
)
PATCHES=(
  "01-occ_impl-shapes.py.diff"
  "02-occ_impl-exporters-vtk.py.diff"
  "03-occ_impl-assembly.py.diff"
  "04-occ_impl-exporters-assembly.py.diff"
)

# A file is considered "patched" when it no longer imports vtkmodules/OCP.IVtk*
# at module (top) level — the exact marker the TE-001.1 patch removes.
is_patched() {
  local f="$1"
  ! grep -Eq '^from (vtkmodules|OCP\.IVtk)' "${f}"
}

patched_count=0
for f in "${FILES[@]}"; do
  target="${CADQUERY_DIR}/${f}"
  if [ ! -f "${target}" ]; then
    echo "expected cadquery source file not found: ${target}" >&2
    echo "this indicates an unexpected cadquery package layout — refusing to guess" >&2
    exit 1
  fi
  if is_patched "${target}"; then
    patched_count=$((patched_count + 1))
  fi
done

if [ "${patched_count}" -eq "${#FILES[@]}" ]; then
  echo "== apply-cadquery-novtk-patch: all ${#FILES[@]} files already patched — idempotent no-op =="
elif [ "${patched_count}" -ne 0 ]; then
  echo "inconsistent patch state: ${patched_count}/${#FILES[@]} files already patched, the rest are not." >&2
  echo "Refusing to guess which is correct — inspect ${CADQUERY_DIR}/occ_impl/ manually." >&2
  exit 1
else
  echo "== apply-cadquery-novtk-patch: applying ${#FILES[@]} patch(es) against unpatched upstream cadquery 2.8.0 =="
  for i in "${!FILES[@]}"; do
    target="${CADQUERY_DIR}/${FILES[$i]}"
    patchfile="${PATCH_DIR}/${PATCHES[$i]}"
    echo "  patching ${FILES[$i]}"
    if ! patch --fuzz=0 "${target}" < "${patchfile}"; then
      echo "" >&2
      echo "FAILED to apply ${patchfile} to ${target}." >&2
      echo "This means the installed cadquery content does not match what this patch" >&2
      echo "expects (e.g. a different cadquery version) — refusing to force-apply." >&2
      echo "Investigate the upstream version / regenerate the patch from a real diff" >&2
      echo "against the exact pinned cadquery==2.8.0 release before retrying." >&2
      exit 1
    fi
  done
fi

echo "== apply-cadquery-novtk-patch: post-patch verification =="
for f in "${FILES[@]}"; do
  target="${CADQUERY_DIR}/${f}"
  if ! is_patched "${target}"; then
    echo "post-patch verification FAILED: top-level VTK import still present in ${target}" >&2
    exit 1
  fi
done

"${TARGET_PYTHON}" - <<'PY'
import sys
sys.path.insert(0, ".")
from tools.poc.novtk.vtk_import_blocker import install
install()
import cadquery
print(
    "No-VTK patch verified active: import cadquery succeeded under "
    "VTKImportBlocker ->", cadquery.__version__,
)
PY

echo "== apply-cadquery-novtk-patch: PASS =="
