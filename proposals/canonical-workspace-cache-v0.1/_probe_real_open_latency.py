"""Time real open commands from frozen trees on one copied live ledger."""

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
CAND = "ec236760072cf20d3a65df3eebd4c4075e86f79e64971b59375e4937fb3d956f"
LIVE_STATE = Path(r"D:\CodexData\home\method-state")
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
PARENT = "wf-20260716-064901-72e801"
OUT = HERE / "_probe_real_open_latency.out.json"
ORDER = ["baseline", "candidate", "candidate", "baseline", "baseline", "candidate"]


def run_open(label, digest, state_root, sequence):
    script = HERE / "artifacts" / digest / "solve-with-weilan" / "scripts" / "weilan_trace.py"
    branch = f"canonical-cache-latency-{sequence:02d}-{label}"
    argv = [
        sys.executable, "-X", "utf8", str(script), "open",
        "--level", "L2", "--workspace", WORKSPACE, "--scope", SCOPE,
        "--branch", branch, "--relation", "fork", "--parent", PARENT,
        "--problem", "Isolated copied-ledger latency sample",
        "--success", "Open returns successfully under the same fixed budget",
        "--budget", "One open command; copied ledger; no deployment",
    ]
    env = os.environ.copy()
    env["WEILAN_METHOD_HOME"] = str(state_root)
    started = time.perf_counter()
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=240,
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
        "elapsed_s": round(elapsed, 3),
        "returncode": proc.returncode,
        "frame_id": frame_id,
        "stdout_bytes": len(proc.stdout.encode("utf-8")),
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
    with tempfile.TemporaryDirectory(prefix="wl-cache-open-") as temp:
        copied_state = Path(temp) / "method-state"
        shutil.copytree(LIVE_STATE, copied_state)
        runs = []
        for sequence, label in enumerate(ORDER, 1):
            digest = BASE if label == "baseline" else CAND
            runs.append(run_open(label, digest, copied_state, sequence))
    baseline = summarize(runs, "baseline")
    candidate = summarize(runs, "candidate")
    all_rc_zero = all(row["returncode"] == 0 and row["frame_id"] for row in runs)
    result = {
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "subject": "real open command against one copied snapshot of the live ledger",
        "live_state_source": str(LIVE_STATE),
        "workspace": WORKSPACE,
        "scope": SCOPE,
        "parent": PARENT,
        "timeout_s_per_run": 240,
        "run_order": ORDER,
        "runs": runs,
        "baseline": baseline,
        "candidate": candidate,
        "all_runs_returned_open_frames": bool(all_rc_zero),
        "median_speedup_x": round(baseline["median_s"] / candidate["median_s"], 3),
        "candidate_median_lower": candidate["median_s"] < baseline["median_s"],
        "boundary": (
            "This is the real open code path and a full copied live ledger, but not a "
            "deployment or a production-ledger write. Host load is uncontrolled; three "
            "samples per arm bound observation, not a universal latency guarantee."
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    passed = all_rc_zero and baseline["n"] == candidate["n"] == 3 and result["candidate_median_lower"]
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
