"""TE-001 OS-level evidence probe (section 20).

Runs the checkpoint sequence up to (and including) the first reachable
checkpoint inside a live, held-open subprocess so the orchestrator can run
``lsof -p PID`` / ``vmmap PID`` against a real, running process before it
exits. Not a general-purpose harness — scoped to TE-001 only.

Protocol: writes ``READY <status>`` to stdout and then blocks reading a line
from stdin before exiting, giving the parent a window to inspect the process.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.poc.novtk.vtk_import_blocker import install as install_blocker  # noqa: E402


def main() -> int:
    install_blocker()
    try:
        import cadquery  # noqa: F401

        status = "import-ok"
    except Exception as exc:
        status = f"import-failed:{type(exc).__name__}"

    print(f"READY {status}", flush=True)
    sys.stdin.readline()  # block until the orchestrator signals continue
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
