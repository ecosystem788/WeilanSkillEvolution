"""Alternating peak-heap driver for the signed call site, on production state.

Acceptance item 4 of the co-signature: "峰值堆增量须报；超过 +25 MB 即停下重议".
The delegated receipt reported +0.1 MB, measured on a compact sandbox. This
driver takes the same measurement against the as-found method-state corpus,
alternating arms with one discarded warm-up each and one process per sample.
Read-only: build_episode_index_value returns a value and never writes.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "_probe_20260802_review_ab_branch.py"
SCRIPT = r"D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py"
SAMPLES = 3


def run(memo):
    argv = [sys.executable, str(PROBE), "--script", SCRIPT, "--mem"]
    if memo:
        argv.append("--memo")
    proc = subprocess.run(argv, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace")[:400])
    return json.loads(proc.stdout.decode("utf-8").strip())


def median(values):
    return sorted(values)[len(values) // 2]


def main():
    report = {"warmup": {}, "samples": {"baseline": [], "memo": []}}
    for memo in (False, True):
        report["warmup"]["memo" if memo else "baseline"] = run(memo)
    for _ in range(SAMPLES):
        for memo in (False, True):
            report["samples"]["memo" if memo else "baseline"].append(run(memo))
    summary = {}
    for arm in ("baseline", "memo"):
        peaks = [s["peak_python_heap_mb"] for s in report["samples"][arm]]
        summary[arm] = {"peaks_mb": peaks, "median_mb": median(peaks),
                        "range_mb": [min(peaks), max(peaks)]}
    delta = round(summary["memo"]["median_mb"] - summary["baseline"]["median_mb"], 1)
    summary["median_delta_mb"] = delta
    summary["exceeds_25mb_stop_line"] = delta > 25
    summary["note"] = "tracemalloc distorts wall clock; only the heap figures are load-bearing here"
    report["summary"] = summary
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
