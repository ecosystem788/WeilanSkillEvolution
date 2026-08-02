"""Read-only review probe: which branch of collapse_trace_registry did the A/B measure?

`collapse_trace_registry` (weilan_trace.py:4470) rebuilds the episode index only
when `episode_index_is_fresh` is False. The memo can only save work on the
rebuild branch: without a memo, `episode_index_is_fresh` -> `scoped_frame_paths`
scans and reads every scoped frame file, and `build_episode_index_value` then
scans and reads them again. On the fresh branch there is exactly one corpus
read, so `derivation_memo_scope` is structurally a no-op there.

This probe runs the same signed call site as `_probe_20260802_advisory_ab.py`
(`attach_trace_advisory_result` whole, with or without the memo wrapper) and
additionally records, per sample, how many times `build_episode_index_value`
actually ran. That number is the branch witness the delegated A/B receipt does
not carry.

--stale forces the branch a real `open` is always in: `command_open_lineaged`
writes its frame events before the advisory call, so the on-disk index's
`source_state` can no longer match. It is forced by making `load_episode_index`
return None for the timed call only; nothing is written either way
(`build_episode_index_value` returns a value, `rebuild_episode_index` is never
called).

Usage (one sample per process):
  python _probe_20260802_review_ab_branch.py --script <path> [--memo] [--stale] [--mem]
"""

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
import time
import tracemalloc

MATCHING_TEXT = (
    "Advisory budget prose is enough to make agents stay under hard evaluation budgets."
)
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"


def load_trace(path):
    script_dir = str(pathlib.Path(path).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("weilan_trace_review_branch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--memo", action="store_true")
    parser.add_argument("--stale", action="store_true")
    parser.add_argument("--mem", action="store_true")
    parser.add_argument("--text", default=MATCHING_TEXT)
    args = parser.parse_args()

    wt = load_trace(args.script)
    workspace = wt.canonical_workspace(WORKSPACE)
    scope = wt.normalize_scope(SCOPE)

    builds = {"count": 0}
    real_build = wt.build_episode_index_value

    def counting_build(ws, sc):
        builds["count"] += 1
        return real_build(ws, sc)

    wt.build_episode_index_value = counting_build
    if args.stale:
        wt.load_episode_index = lambda ws, sc: None

    if args.mem:
        tracemalloc.start()
    output = {}
    started = time.perf_counter()
    if args.memo:
        with wt.derivation_memo_scope():
            wt.attach_trace_advisory_result(output, workspace, scope, args.text)
    else:
        wt.attach_trace_advisory_result(output, workspace, scope, args.text)
    elapsed = time.perf_counter() - started

    payload = json.dumps(
        output, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    result = {
        "arm": "candidate-memo" if args.memo else "baseline-nomemo",
        "index_state": "forced-stale" if args.stale else "as-found",
        "build_episode_index_calls": builds["count"],
        "advisory_count": len(output.get("trace_advisories", [])),
        "advisory_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "seconds_callsite": round(elapsed, 3),
        "script": args.script,
    }
    if args.mem:
        _, peak = tracemalloc.get_traced_memory()
        result["peak_python_heap_mb"] = round(peak / 1e6, 1)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
