"""Alternating driver for _probe_20260802_review_ab_branch.py.

Same temperature discipline the co-signature requires: one discarded warm-up per
arm, arms strictly alternated, >=3 kept samples each, one fresh process per
sample. Runs both index states: as-found (what the delegated A/B measured) and
forced-stale (the branch a real open is always in).
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "_probe_20260802_review_ab_branch.py"
SCRIPT = r"D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py"
SAMPLES = 3


def run(memo, stale, mem=False):
    argv = [sys.executable, str(PROBE), "--script", SCRIPT]
    if memo:
        argv.append("--memo")
    if stale:
        argv.append("--stale")
    if mem:
        argv.append("--mem")
    proc = subprocess.run(argv, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"memo={memo} stale={stale} rc={proc.returncode}: "
            + proc.stderr.decode("utf-8", "replace")[:400]
        )
    return json.loads(proc.stdout.decode("utf-8").strip())


def median(values):
    return sorted(values)[len(values) // 2]


def main():
    modes = sys.argv[1:] or ["as-found", "forced-stale"]
    report = {}
    for mode in modes:
        stale = mode == "forced-stale"
        block = {"warmup": {}, "samples": {"baseline": [], "memo": []}}
        for memo in (False, True):
            block["warmup"]["memo" if memo else "baseline"] = run(memo, stale)
        for _ in range(SAMPLES):
            for memo in (False, True):
                block["samples"]["memo" if memo else "baseline"].append(run(memo, stale))
        summary = {}
        for arm in ("baseline", "memo"):
            seconds = [s["seconds_callsite"] for s in block["samples"][arm]]
            summary[arm] = {
                "seconds": seconds,
                "median": median(seconds),
                "range": [min(seconds), max(seconds)],
                "build_calls": sorted({s["build_episode_index_calls"] for s in block["samples"][arm]}),
                "advisory_counts": sorted({s["advisory_count"] for s in block["samples"][arm]}),
                "payload_sha256": sorted({s["advisory_payload_sha256"] for s in block["samples"][arm]}),
            }
        lo = summary["baseline"]["range"]
        hi = summary["memo"]["range"]
        summary["ranges_overlap"] = not (lo[1] < hi[0] or hi[1] < lo[0])
        summary["memo_over_baseline"] = (
            round(summary["memo"]["median"] / summary["baseline"]["median"], 3)
            if summary["baseline"]["median"]
            else None
        )
        summary["payload_equal_across_arms"] = (
            summary["baseline"]["payload_sha256"] == summary["memo"]["payload_sha256"]
        )
        block["summary"] = summary
        block["memory"] = {
            ("memo" if memo else "baseline"): run(memo, stale, mem=True)
            for memo in (False, True)
        }
        report[mode] = block
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
