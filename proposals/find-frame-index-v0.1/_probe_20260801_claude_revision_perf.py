"""Read-only: Claude's INDEPENDENT re-measurement of the revised frozen candidate.

Why this exists rather than a rerun of _probe_20260801_frozen_tree_perf.py: that
probe hard-codes CAND = 794022d9..., the pre-revision candidate. The revision
(guarded lookup) is fb16689a..., and the numbers Codex reported for it were never
archived -- they exist only as prose in peer-chat. This probe pins them to a file
in the tree, measured by the reviewer rather than the implementer.

Same shape as the probe it supersedes: two frozen trees, own subprocess each,
interleaved b,c,b,c so ledger growth mid-probe shows up as a stdout mismatch
instead of hiding behind a favourable ordering. Writes nothing outside stdout.
"""

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import types

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996"
HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"


def child(scripts_dir):
    sys.path.insert(0, scripts_dir)
    import weilan_trace as wt  # noqa: E402 -- must follow the sys.path setup

    args = types.SimpleNamespace(workspace=WORKSPACE, scope=SCOPE)
    buffer = io.StringIO()
    real_stdout, sys.stdout = sys.stdout, buffer
    started = time.perf_counter()
    try:
        rc = wt.command_lineage_show(args)
    finally:
        sys.stdout = real_stdout
    elapsed = time.perf_counter() - started
    payload = buffer.getvalue()
    parsed = json.loads(payload)
    encoded = payload.encode("utf-8")
    json.dump({
        "rc": rc,
        "elapsed_s": round(elapsed, 3),
        "stdout_sha256": hashlib.sha256(encoded).hexdigest(),
        "stdout_bytes": len(encoded),
        "record_count": parsed.get("record_count"),
        "valid": parsed.get("valid"),
    }, sys.stdout, ensure_ascii=False)


def drive(label, digest):
    scripts_dir = os.path.join(HERE, "artifacts", digest, "solve-with-weilan", "scripts")
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", os.path.abspath(__file__), "--child", scripts_dir],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        return {"label": label, "child_returncode": proc.returncode,
                "stderr_tail": proc.stderr.strip()[-500:]}
    row = json.loads(proc.stdout)
    row["label"] = label
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child")
    args = parser.parse_args()
    if args.child:
        child(args.child)
        return

    runs = []
    for _ in range(2):
        runs.append(drive("baseline", BASE))
        runs.append(drive("candidate", CAND))

    digests = {row.get("stdout_sha256") for row in runs}
    baseline_times = [r["elapsed_s"] for r in runs if r.get("label") == "baseline"]
    candidate_times = [r["elapsed_s"] for r in runs if r.get("label") == "candidate"]
    ok = baseline_times and candidate_times and min(candidate_times) > 0
    result = {
        "probe": "claude_revision_perf",
        "measured_by": "claude (reviewer, not implementer)",
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "workspace": WORKSPACE,
        "scope": SCOPE,
        "run_order": [r.get("label") for r in runs],
        "runs": runs,
        "all_stdout_byte_identical": len(digests) == 1 and None not in digests,
        "distinct_stdout_digests": sorted(d for d in digests if d),
        "baseline_elapsed_s": baseline_times,
        "candidate_elapsed_s": candidate_times,
        "min_run_speedup_x": round(min(baseline_times) / min(candidate_times), 2) if ok else None,
        "mean_ratio_speedup_x": (
            round((sum(baseline_times) / len(baseline_times))
                  / (sum(candidate_times) / len(candidate_times)), 2) if ok else None
        ),
        "note": (
            "Byte-equality across all four runs also means the ledger did not grow "
            "mid-probe. Absolute seconds are not comparable across probe runs: the "
            "ledger grows between them, and this machine's load is not controlled. "
            "The speedup ratio, measured interleaved, is the comparable quantity."
        ),
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
