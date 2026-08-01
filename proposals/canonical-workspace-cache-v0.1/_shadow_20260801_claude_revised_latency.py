"""Fresh equal-budget real-open latency trial bound to the REVISED candidate 8602bb0f.

Written independently by Claude (non-author of the candidate) to remove the one caveat the
package itself declares: the archived latency receipt names the previous candidate
ec236760 and is therefore inherited implementation evidence, not a trial against the
revised content address. Same shape as the author's probe (three samples per arm,
interleaved, 240 s per-run bound, one temporary copy of the live ledger), but the
candidate digest is the revised one and each run records the sha256 of the runtime_core.py
that was actually executed.

Read-only with respect to the production ledger: every open writes into a temp copy.
"""

import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
PRIOR_CAND = "ec236760072cf20d3a65df3eebd4c4075e86f79e64971b59375e4937fb3d956f"
LIVE_STATE = Path(r"D:\CodexData\home\method-state")
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
PARENT = "wf-20260716-064901-72e801"
OUT = HERE / "_shadow_20260801_claude_revised_latency.out.json"
ORDER = ["baseline", "candidate", "candidate", "baseline", "baseline", "candidate"]
TIMEOUT_S = 240


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scripts_dir(digest):
    return HERE / "artifacts" / digest / "solve-with-weilan" / "scripts"


def run_open(label, digest, state_root, sequence):
    script = scripts_dir(digest) / "weilan_trace.py"
    argv = [
        sys.executable, "-X", "utf8", str(script), "open",
        "--level", "L2", "--workspace", WORKSPACE, "--scope", SCOPE,
        "--branch", f"claude-revised-latency-{sequence:02d}-{label}",
        "--relation", "fork", "--parent", PARENT,
        "--problem", "Isolated copied-ledger latency sample bound to the revised candidate",
        "--success", "Open returns successfully under the same fixed budget",
        "--budget", "One open command; copied ledger; no deployment",
    ]
    env = os.environ.copy()
    env["WEILAN_METHOD_HOME"] = str(state_root)
    started = time.perf_counter()
    proc = subprocess.run(
        argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, timeout=TIMEOUT_S,
    )
    elapsed = time.perf_counter() - started
    frame_id = None
    try:
        frame_id = json.loads(proc.stdout).get("frame_id")
    except (ValueError, AttributeError):
        pass
    return {
        "label": label,
        "sequence": sequence,
        "artifact_hash": digest,
        "executed_runtime_core_sha256": sha256_file(scripts_dir(digest) / "runtime_core.py"),
        "elapsed_s": round(elapsed, 3),
        "returncode": proc.returncode,
        "frame_id": frame_id,
        "stderr_tail": proc.stderr.strip()[-300:],
    }


def summarize(runs, label):
    values = [row["elapsed_s"] for row in runs if row["label"] == label]
    return {
        "n": len(values),
        "min_s": min(values),
        "max_s": max(values),
        "median_s": round(statistics.median(values), 3),
        "mean_s": round(statistics.mean(values), 3),
        "samples_s": values,
    }


def main():
    runtime_core_sha = {
        digest: sha256_file(scripts_dir(digest) / "runtime_core.py")
        for digest in (BASE, CAND, PRIOR_CAND)
    }
    with tempfile.TemporaryDirectory(prefix="wl-claude-revlat-") as temp:
        copied_state = Path(temp) / "method-state"
        shutil.copytree(LIVE_STATE, copied_state)
        runs = []
        for sequence, label in enumerate(ORDER, 1):
            runs.append(run_open(label, BASE if label == "baseline" else CAND, copied_state, sequence))

    baseline = summarize(runs, "baseline")
    candidate = summarize(runs, "candidate")
    all_ok = all(row["returncode"] == 0 and row["frame_id"] for row in runs)
    result = {
        "probe": "claude independent equal-budget real-open latency, revised candidate",
        "baseline_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "prior_candidate_artifact_hash": PRIOR_CAND,
        "runtime_core_sha256_by_artifact": runtime_core_sha,
        "revised_and_prior_candidate_share_runtime_core": (
            runtime_core_sha[CAND] == runtime_core_sha[PRIOR_CAND]
        ),
        "candidate_runtime_core_differs_from_baseline": (
            runtime_core_sha[CAND] != runtime_core_sha[BASE]
        ),
        "live_state_source": str(LIVE_STATE),
        "workspace": WORKSPACE,
        "scope": SCOPE,
        "parent": PARENT,
        "timeout_s_per_run": TIMEOUT_S,
        "run_order": ORDER,
        "runs": runs,
        "baseline": baseline,
        "candidate": candidate,
        "all_runs_returned_open_frames": bool(all_ok),
        "median_speedup_x": round(baseline["median_s"] / candidate["median_s"], 3) if candidate["median_s"] else None,
        "candidate_median_lower": candidate["median_s"] < baseline["median_s"],
        "arms_have_disjoint_ranges": baseline["min_s"] > candidate["max_s"],
        "worst_cross_arm_ratio_x": round(baseline["min_s"] / candidate["max_s"], 3) if candidate["max_s"] else None,
        "boundary": (
            "Real open code path on a full copied live ledger, not a deployment and not a "
            "production-ledger write. Host load is uncontrolled and three samples per arm "
            "bound an observation, not a universal latency floor."
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    passed = all_ok and baseline["n"] == candidate["n"] == 3 and result["candidate_median_lower"]
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
