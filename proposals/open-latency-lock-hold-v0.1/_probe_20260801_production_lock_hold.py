"""Measure the real lineage-lock hold window of a production `open`.

Writes nothing to the ledger. The probe acquires the production lineage lock
and releases it in the same breath; the datum is *how long it was blocked*,
which equals the tail of the hold window of whatever open was in flight.

Run it concurrently with a real `open`, started `delay_s` after the open:
    lock_hold_lower_bound = delay_s + blocked_s

It is a lower bound, not the hold: the probe cannot see the part of the window
that elapsed before it started asking, beyond the delay it waited.

Usage:  python _probe_20260801_production_lock_hold.py <delay_s> <out_json>
"""
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts"
sys.path.insert(0, SCRIPTS)

import weilan_trace as wt  # noqa: E402

WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"


def main():
    delay_s = float(sys.argv[1])
    out_path = Path(sys.argv[2])

    workspace = wt.canonical_workspace(WORKSPACE)
    scope = wt.normalize_scope(SCOPE)

    # The workspace-wide contract lock, not the lineage lock: contract_fence
    # (transaction.py:317) takes `.workspace-contract.lock` FIRST and wraps the
    # whole of command_open_lineaged_fenced (weilan_trace.py:538), and it is the
    # lock the recorded production timeouts actually名 (2026-07-22 / 07-24).
    which = sys.argv[3] if len(sys.argv) > 3 else "workspace"
    if which == "lineage":
        lock_path = wt.lineage_directory(workspace, scope) / ".lineage.lock"
    else:
        from transaction import contract_fence_directory

        lock_path = (
            contract_fence_directory(wt.state_root(), wt.workspace_key(workspace))
            / ".workspace-contract.lock"
        )

    t0 = time.monotonic()
    time.sleep(delay_s)

    acquired = False
    error = None
    start = time.monotonic()
    try:
        with wt.exclusive_file_lock(lock_path):
            acquired = True
            held_at = time.monotonic()
    except Exception as exc:  # noqa: BLE001 - the failure mode is a datum too
        error = {"type": type(exc).__name__, "message": str(exc)}
        held_at = time.monotonic()
    blocked_s = held_at - start

    report = {
        "lock_kind": which,
        "lock_path": str(lock_path),
        "delay_s": delay_s,
        "acquired": acquired,
        "blocked_s": round(blocked_s, 3),
        "lock_hold_lower_bound_s": round(delay_s + blocked_s, 3),
        "error": error,
        "probe_wall_s": round(time.monotonic() - t0, 3),
        "note": (
            "blocked_s>~0 means another process held the lock named in "
            "lock_path for at least that long after this probe started asking; "
            "the probe itself held it for microseconds and wrote nothing"
        ),
        "env_lock_timeout_s": os.environ.get("WEILAN_LOCK_TIMEOUT_S"),
    }
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
