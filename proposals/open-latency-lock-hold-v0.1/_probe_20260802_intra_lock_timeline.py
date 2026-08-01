"""Read-only probe: measure the INTRA-LOCK timeline of `weilan_trace.py open`.

Closes boundary #2 of proposals/open-latency-lock-hold-v0.1/FINDING.md, which said:
"advisory occupies 96% of the lock hold" was static-analysis + profile stitched
together, NOT measured. This probe measures the decomposition from OUTSIDE the
process, without instrumenting the machine:

    t_spawn ............ open subprocess starts (upper bound on lock-acquire)
    t_frame ............ frame jsonl appears in frames/<date>/   (weilan_trace.py:667)
    t_heads ............ lineage heads file mtime changes        (weilan_trace.py:677)
    t_release .......... a separate contender process, blocked on the SAME
                         workspace-level .workspace-contract.lock, finally
                         acquires it => open released all three locks

Everything from :538 (contract_fence) to :688 is inside the three locks, so
[t_heads, t_release] is the post-write intra-lock window, and per source there
is exactly one thing in it: attach_trace_advisory_result (:685) + print (:688)
+ fence teardown. No write happens after :677.

Safety: runs entirely against a COPIED ledger selected by WEILAN_METHOD_HOME.
Production ledger is never opened for write. Frames are created with
`relation fork` from a CLOSED head onto throwaway branch names, so the copy's
main branch head never moves.

Usage:
    python _probe_20260802_intra_lock_timeline.py --ledger <copy> --parent <closed frame id>
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
TRACE = SCRIPTS / "weilan_trace.py"
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
POLL_S = 0.005

CONTENDER_SRC = r'''
import json, sys, time
from pathlib import Path
sys.path.insert(0, r"{scripts}")
from runtime_core import exclusive_file_lock
path = Path(sys.argv[1])
t_request = time.time()
with exclusive_file_lock(path):
    t_acquire = time.time()
print(json.dumps({{"t_request": t_request, "t_acquire": t_acquire,
                  "blocked_s": t_acquire - t_request}}))
'''


def lock_and_heads_paths(ledger):
    env_backup = os.environ.get("WEILAN_METHOD_HOME")
    os.environ["WEILAN_METHOD_HOME"] = str(ledger)
    sys.path.insert(0, str(SCRIPTS))
    from runtime_core import state_root, workspace_key, canonical_workspace  # noqa
    import weilan_trace as wt

    workspace = canonical_workspace(WORKSPACE)
    scope = wt.normalize_scope(SCOPE)
    from transaction import contract_fence_directory

    lock = contract_fence_directory(state_root(), workspace_key(workspace)) / ".workspace-contract.lock"
    heads = wt.lineage_heads_path(workspace, scope)
    if env_backup is None:
        del os.environ["WEILAN_METHOD_HOME"]
    else:
        os.environ["WEILAN_METHOD_HOME"] = env_backup
    return Path(lock), Path(heads)


def mtime_ns(path):
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def measure_startup(env, n=3):
    """Bound the pre-lock cost: interpreter import + argparse, no ledger work."""
    samples = []
    for _ in range(n):
        t0 = time.time()
        subprocess.run([sys.executable, str(TRACE), "--help"],
                       env=env, capture_output=True)
        samples.append(time.time() - t0)
    return samples


def one_trial(ledger, parent, branch, lock_path, heads_path, contender_src, env,
              contender_delay_s):
    frames_dir = ledger / "frames" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    frames_dir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in frames_dir.iterdir()}
    heads_before = mtime_ns(heads_path)

    cmd = [sys.executable, str(TRACE), "open",
           "--workspace", WORKSPACE, "--scope", SCOPE,
           "--problem", "intra-lock timeline probe (copied ledger)",
           "--success", "post-write intra-lock window measured",
           "--level", "L2", "--relation", "fork",
           "--parent", parent, "--branch", branch]

    t_spawn = time.time()
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    t_frame = None
    t_heads = None
    contender = None
    while proc.poll() is None:
        now = time.time()
        if t_frame is None:
            new = {p.name for p in frames_dir.iterdir()} - before
            if new:
                t_frame = time.time()
        if t_heads is None and mtime_ns(heads_path) != heads_before:
            t_heads = time.time()
        if contender is None and now - t_spawn >= contender_delay_s:
            contender = subprocess.Popen([sys.executable, "-c", contender_src,
                                          str(lock_path)],
                                         env=env, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        time.sleep(POLL_S)
    out, err = proc.communicate()
    t_exit = time.time()
    if contender is None:
        contender = subprocess.Popen([sys.executable, "-c", contender_src, str(lock_path)],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cout, cerr = contender.communicate()
    try:
        cdata = json.loads(cout.decode("utf-8", "replace").strip())
    except Exception as exc:
        cdata = {"parse_error": str(exc),
                 "stdout": cout.decode("utf-8", "replace")[:400],
                 "stderr": cerr.decode("utf-8", "replace")[:400]}

    rec = {
        "branch": branch,
        "rc": proc.returncode,
        "stderr_tail": err.decode("utf-8", "replace")[-300:],
        "t_spawn": t_spawn,
        "t_frame": t_frame,
        "t_heads": t_heads,
        "t_exit": t_exit,
        "contender": cdata,
        "wall_s": t_exit - t_spawn,
    }
    t_release = cdata.get("t_acquire")
    if t_release and t_heads:
        rec["post_write_intra_lock_s"] = t_release - t_heads
    if t_release:
        rec["release_after_exit_s"] = t_release - t_exit
        rec["hold_upper_denominator_s"] = t_release - t_spawn
    if t_frame:
        rec["spawn_to_frame_s"] = t_frame - t_spawn
    if t_frame and t_heads:
        rec["frame_to_heads_s"] = t_heads - t_frame
    if rec.get("post_write_intra_lock_s") and rec.get("hold_upper_denominator_s"):
        rec["post_write_share_of_wall"] = (
            rec["post_write_intra_lock_s"] / rec["hold_upper_denominator_s"]
        )
    rec["contender_started_late_enough"] = bool(cdata.get("blocked_s", 0) > 0.5)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--parent", required=True)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--warmups", type=int, default=1)
    ap.add_argument("--contender-delay", type=float, default=1.5)
    ap.add_argument("--tag", default="a")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ledger = Path(args.ledger)
    assert ledger.exists(), ledger
    assert str(ledger).lower() != str(Path(r"D:\CodexData\home\method-state")).lower()

    env = dict(os.environ)
    env["WEILAN_METHOD_HOME"] = str(ledger)
    env["PYTHONIOENCODING"] = "utf-8"

    lock_path, heads_path = lock_and_heads_paths(ledger)
    contender_src = CONTENDER_SRC.format(scripts=str(SCRIPTS))

    result = {
        "probe": "intra_lock_timeline",
        "ledger": str(ledger),
        "production_ledger_touched": False,
        "lock_path": str(lock_path),
        "heads_path": str(heads_path),
        "parent": args.parent,
        "poll_s": POLL_S,
        "startup_help_s": measure_startup(env),
        "warmups": [],
        "trials": [],
    }
    for i in range(args.warmups):
        result["warmups"].append(
            one_trial(ledger, args.parent, f"probe-{args.tag}-warm-{i}", lock_path,
                      heads_path, contender_src, env, args.contender_delay))
    for i in range(args.trials):
        result["trials"].append(
            one_trial(ledger, args.parent, f"probe-{args.tag}-t{i}", lock_path,
                      heads_path, contender_src, env, args.contender_delay))

    ok = [t for t in result["trials"]
          if t["rc"] == 0 and t.get("post_write_share_of_wall")
          and t["contender_started_late_enough"]]
    if ok:
        shares = sorted(t["post_write_share_of_wall"] for t in ok)
        posts = sorted(t["post_write_intra_lock_s"] for t in ok)
        walls = sorted(t["wall_s"] for t in ok)
        result["summary"] = {
            "n_valid": len(ok),
            "post_write_share_median": shares[len(shares) // 2],
            "post_write_share_min": shares[0],
            "post_write_share_max": shares[-1],
            "post_write_intra_lock_median_s": posts[len(posts) // 2],
            "wall_median_s": walls[len(walls) // 2],
        }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps(result.get("summary", {"n_valid": 0}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
