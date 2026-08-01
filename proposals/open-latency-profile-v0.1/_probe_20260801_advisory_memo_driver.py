"""Alternating A/B driver for _probe_20260801_advisory_memo_scope.py.

Temperature discipline (per the 2026-08-01 finding that cache warmth swings wider
than the code version): one warm-up sample per arm that is discarded, then the two
arms strictly alternated, >=3 kept samples each, one fresh process per sample.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "_probe_20260801_advisory_memo_scope.py"
SAMPLES = 3


def run(arm, mem=False):
    argv = [sys.executable, str(PROBE), "--arm", arm]
    if mem:
        argv.append("--mem")
    proc = subprocess.run(argv, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{arm} rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[:400]}")
    return json.loads(proc.stdout.decode("utf-8").strip())


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def main():
    report = {"warmup": {}, "samples": {"nomemo": [], "memo": []}}
    for arm in ("nomemo", "memo"):
        report["warmup"][arm] = run(arm)
    for _ in range(SAMPLES):
        for arm in ("nomemo", "memo"):
            report["samples"][arm].append(run(arm))
    report["summary"] = {}
    for arm in ("nomemo", "memo"):
        totals = [s["seconds_total"] for s in report["samples"][arm]]
        report["summary"][arm] = {
            "totals": totals,
            "median_total": median(totals),
            "freshness": [s["seconds_freshness"] for s in report["samples"][arm]],
            "build": [s["seconds_build"] for s in report["samples"][arm]],
            "fresh_values": sorted({s["fresh"] for s in report["samples"][arm]}),
            "episode_counts": sorted({s.get("episode_count") for s in report["samples"][arm]}),
        }
    a = report["summary"]["nomemo"]["median_total"]
    b = report["summary"]["memo"]["median_total"]
    report["summary"]["memo_over_nomemo"] = round(b / a, 3) if a else None
    report["summary"]["seconds_saved_median"] = round(a - b, 3)
    report["memory"] = {arm: run(arm, mem=True) for arm in ("nomemo", "memo")}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
