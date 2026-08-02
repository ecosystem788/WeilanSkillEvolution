"""Same-session four-arm driver: is the unsigned call site as expensive as the signed one?

The 0.499x from 19:32 (open site) and any figure measured for the event site in a
separate session cannot be compared -- cache warmth dominates code version on this
box (measured 4.66x cold/warm against 2.31x baseline/candidate on 08-01). So this
driver alternates all four arms inside one session:

  open:685   x {baseline-nomemo, candidate-memo}   <- the site the signature covers
  event:805  x {baseline-nomemo, candidate-memo}   <- the site it does not

Round-robin over the four arms, one warm-up round discarded, one sample per
process, same as-found corpus throughout. Nothing is written.

Usage:
  python _probe_20260802_twosite_driver.py --script <path> [--samples 3]
"""

import argparse
import json
import pathlib
import statistics
import subprocess
import sys

PROBE = pathlib.Path(__file__).with_name("_probe_20260802_event_callsite_ab.py")
ARMS = [
    ("open", False),
    ("open", True),
    ("event", False),
    ("event", True),
]


def arm_name(site, memo):
    return "%s/%s" % (site, "candidate-memo" if memo else "baseline-nomemo")


def run_sample(script, site, memo):
    cmd = [sys.executable, str(PROBE), "--script", script, "--site", site]
    if memo:
        cmd.append("--memo")
    completed = subprocess.run(cmd, capture_output=True)
    if completed.returncode != 0:
        raise SystemExit(
            "probe failed rc=%d\n%s" % (completed.returncode, completed.stderr.decode("utf-8", "replace"))
        )
    return json.loads(completed.stdout.decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()

    warmups = {arm_name(s, m): run_sample(args.script, s, m)["seconds_callsite"] for s, m in ARMS}

    collected = {arm_name(s, m): [] for s, m in ARMS}
    for _ in range(args.samples):
        for site, memo in ARMS:
            collected[arm_name(site, memo)].append(run_sample(args.script, site, memo))

    summary = {}
    for name, samples in collected.items():
        values = [s["seconds_callsite"] for s in samples]
        summary[name] = {
            "n": len(values),
            "median": round(statistics.median(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "samples": values,
            "build_episode_index_calls": sorted({s["build_episode_index_calls"] for s in samples}),
            "advisory_payload_sha256": sorted({s["advisory_payload_sha256"] for s in samples}),
            "advisory_count": sorted({s["advisory_count"] for s in samples}),
        }

    open_ratio = summary["open/candidate-memo"]["median"] / summary["open/baseline-nomemo"]["median"]
    event_ratio = summary["event/candidate-memo"]["median"] / summary["event/baseline-nomemo"]["median"]
    baseline_site_ratio = (
        summary["event/baseline-nomemo"]["median"] / summary["open/baseline-nomemo"]["median"]
    )
    result = {
        "design": "round-robin over four arms in one session, one warm-up round discarded",
        "metric": "seconds_callsite",
        "warmups_discarded": warmups,
        "arms": summary,
        "memo_ratio_open_site": round(open_ratio, 3),
        "memo_ratio_event_site": round(event_ratio, 3),
        "unsigned_over_signed_baseline_ratio": round(baseline_site_ratio, 3),
        "sample_input": {
            key: collected["event/baseline-nomemo"][0][key]
            for key in ("sample_frame_file", "sample_event_type", "resolved_scope", "text_len")
        },
        "script": args.script,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
