"""Alternating memo vs buildonly: does making the freshness check free still help
once a memo scope exists? Same temperature discipline as the memo driver."""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "_probe_20260801_advisory_memo_scope.py"
ARMS = ("memo", "buildonly")
SAMPLES = 3


def run(arm):
    proc = subprocess.run([sys.executable, str(PROBE), "--arm", arm], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{arm} rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[:400]}")
    return json.loads(proc.stdout.decode("utf-8").strip())


def median(values):
    return sorted(values)[len(values) // 2]


report = {"warmup": {arm: run(arm) for arm in ARMS}, "samples": {arm: [] for arm in ARMS}}
for _ in range(SAMPLES):
    for arm in ARMS:
        report["samples"][arm].append(run(arm))
report["summary"] = {
    arm: {
        "totals": [s["seconds_total"] for s in report["samples"][arm]],
        "median_total": median([s["seconds_total"] for s in report["samples"][arm]]),
        "episode_counts": sorted({s.get("episode_count") for s in report["samples"][arm]}),
    }
    for arm in ARMS
}
m = report["summary"]["memo"]["median_total"]
b = report["summary"]["buildonly"]["median_total"]
report["summary"]["buildonly_minus_memo_seconds"] = round(b - m, 3)
print(json.dumps(report, ensure_ascii=False, indent=2))
