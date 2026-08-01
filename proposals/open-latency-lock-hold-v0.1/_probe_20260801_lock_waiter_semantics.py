"""Read-only probe: what does a second opener actually do while the lineage
lock is held?

Runs entirely inside a fresh temp directory against the real
runtime_core.exclusive_file_lock. Touches no ledger, no frame, no production
lock file.

Two arms:
  A. holder holds for HOLD_S with the default WEILAN_LOCK_TIMEOUT_S -> does the
     waiter block-and-succeed, and for how long?
  B. holder holds for HOLD_S with a *short* configured timeout -> does the
     waiter give up at the configured deadline, and with what error?

Arm B exists because of the retry structure in runtime_core.py:158-176: the
deadline is only checked *after* each msvcrt.locking(LK_LOCK) call returns, and
each such call itself blocks for ~10 one-second retries. So the configured
timeout may not be honoured at sub-10s granularity. This probe measures that
rather than asserting it.

Usage:  python _probe_20260801_lock_waiter_semantics.py
Output: JSON on stdout.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts"
sys.path.insert(0, SCRIPTS)

from runtime_core import exclusive_file_lock  # noqa: E402

HOLDER_SRC = r'''
import os, sys, time
sys.path.insert(0, r"{scripts}")
from runtime_core import exclusive_file_lock
from pathlib import Path
lock_path = Path(sys.argv[1])
hold_s = float(sys.argv[2])
ready = Path(sys.argv[3])
with exclusive_file_lock(lock_path):
    ready.write_bytes(b"held")
    time.sleep(hold_s)
'''


def run_arm(tmp, arm_name, hold_s, waiter_timeout_env):
    lock_path = Path(tmp) / f"{arm_name}.lock"
    ready = Path(tmp) / f"{arm_name}.ready"
    holder_py = Path(tmp) / f"{arm_name}_holder.py"
    holder_py.write_text(HOLDER_SRC.format(scripts=SCRIPTS), encoding="utf-8")

    # stdout/stderr as bytes: text=True would decode as GBK on this host.
    holder = subprocess.Popen(
        [sys.executable, str(holder_py), str(lock_path), str(hold_s), str(ready)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # wait until the holder actually owns the lock, so we measure contention
    # rather than process startup
    spin_deadline = time.monotonic() + 60
    while not ready.exists() and time.monotonic() < spin_deadline:
        if holder.poll() is not None:
            break
        time.sleep(0.02)
    holder_ready = ready.exists()
    held_at = time.monotonic()

    env_before = os.environ.get("WEILAN_LOCK_TIMEOUT_S")
    if waiter_timeout_env is None:
        os.environ.pop("WEILAN_LOCK_TIMEOUT_S", None)
    else:
        os.environ["WEILAN_LOCK_TIMEOUT_S"] = str(waiter_timeout_env)

    acquired = False
    error = None
    start = time.monotonic()
    try:
        with exclusive_file_lock(lock_path):
            acquired = True
    except Exception as exc:  # noqa: BLE001 - the failure mode is the datum
        error = {"type": type(exc).__name__, "message": str(exc)}
    waited_s = time.monotonic() - start

    if env_before is None:
        os.environ.pop("WEILAN_LOCK_TIMEOUT_S", None)
    else:
        os.environ["WEILAN_LOCK_TIMEOUT_S"] = env_before

    out, err = holder.communicate(timeout=180)
    return {
        "arm": arm_name,
        "holder_hold_s": hold_s,
        "waiter_configured_timeout_s": waiter_timeout_env,
        "holder_reached_lock": holder_ready,
        "holder_returncode": holder.returncode,
        "holder_stderr_tail": err.decode("utf-8", "replace")[-400:],
        "waiter_acquired": acquired,
        "waiter_waited_s": round(waited_s, 3),
        "waiter_error": error,
        "seconds_from_hold_start_to_waiter_return": round(
            (start + waited_s) - held_at, 3
        ),
    }


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="weilan_lockprobe_") as tmp:
        # A: holder holds 6s, waiter uses the deployed default (120s)
        results.append(run_arm(tmp, "A_default_timeout", 6.0, None))
        # B: holder holds 25s, waiter configured to give up after 2s
        results.append(run_arm(tmp, "B_short_timeout", 25.0, 2))
    json.dump(
        {
            "lock_impl": "runtime_core.exclusive_file_lock",
            "platform": os.name,
            "default_timeout_s_from_source": 120.0,
            "arms": results,
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
