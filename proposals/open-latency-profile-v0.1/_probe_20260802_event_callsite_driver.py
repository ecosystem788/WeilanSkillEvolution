"""Alternating A/B driver for the second (unsigned) advisory call site.

Same temperature discipline as the signed A/B: alternate arms, discard one
warm-up per arm, one sample per process, three timed samples per arm, both arms
against the same as-found corpus. Records the payload sha256 and the
`build_episode_index_value` call count per sample so the branch actually taken
is a witness in the receipt, not an assumption.

Usage:
  python _probe_20260802_event_callsite_driver.py --script <path> [--samples 3] [--mem]
"""

import argparse
import json
import pathlib
import statistics
import subprocess
import sys

PROBE = pathlib.Path(__file__).with_name("_probe_20260802_event_callsite_ab.py")


def run_sample(script, memo, mem):
    cmd = [sys.executable, str(PROBE), "--script", script]
    if memo:
        cmd.append("--memo")
    if mem:
        cmd.append("--mem")
    completed = subprocess.run(cmd, capture_output=True)
    if completed.returncode != 0:
        raise SystemExit(
            "probe failed rc=%d\n%s" % (completed.returncode, completed.stderr.decode("utf-8", "replace"))
        )
    return json.loads(completed.stdout.decode("utf-8"))


def summarize(samples, key):
    values = [sample[key] for sample in samples]
    return {
        "n": len(values),
        "median": round(statistics.median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--mem", action="store_true")
    args = parser.parse_args()

    warmups = {"baseline-nomemo": run_sample(args.script, False, args.mem),
               "candidate-memo": run_sample(args.script, True, args.mem)}

    arms = {"baseline-nomemo": [], "candidate-memo": []}
    for _ in range(args.samples):
        arms["baseline-nomemo"].append(run_sample(args.script, False, args.mem))
        arms["candidate-memo"].append(run_sample(args.script, True, args.mem))

    metric = "peak_python_heap_mb" if args.mem else "seconds_callsite"
    result = {
        "call_site": "command_event:805",
        "metric": metric,
        "tracemalloc_active": bool(args.mem),
        "warmups_discarded": {name: sample[metric] for name, sample in warmups.items()},
        "arms": {
            name: {
                "summary": summarize(samples, metric),
                "build_episode_index_calls": sorted({s["build_episode_index_calls"] for s in samples}),
                "advisory_payload_sha256": sorted({s["advisory_payload_sha256"] for s in samples}),
                "advisory_count": sorted({s["advisory_count"] for s in samples}),
                "advisory_error": sorted({str(s.get("advisory_error")) for s in samples}),
                "samples": [s[metric] for s in samples],
            }
            for name, samples in arms.items()
        },
        "sample_input": {
            key: arms["baseline-nomemo"][0][key]
            for key in ("sample_frame_file", "sample_event_type", "resolved_scope", "text_len")
        },
        "script": args.script,
    }
    base = result["arms"]["baseline-nomemo"]["summary"]["median"]
    cand = result["arms"]["candidate-memo"]["summary"]["median"]
    result["ratio_candidate_over_baseline"] = round(cand / base, 3) if base else None
    result["intervals_overlap"] = not (
        result["arms"]["candidate-memo"]["summary"]["max"]
        < result["arms"]["baseline-nomemo"]["summary"]["min"]
        or result["arms"]["baseline-nomemo"]["summary"]["max"]
        < result["arms"]["candidate-memo"]["summary"]["min"]
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
