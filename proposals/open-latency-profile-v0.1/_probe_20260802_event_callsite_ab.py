"""Read-only probe: what does the SECOND advisory call site cost?

`attach_trace_advisory_result` has two call sites in weilan_trace.py:

  * `command_open_lineaged_fenced` :685 -- the one the 15:59:34 proposal wrapped
    in `derivation_memo_scope()` and Codex signed at 16:33:55.
  * `command_event` :805 -- fires only for candidate_admitted / holder_selected
    / route_reentered. NOT wrapped by the signed change.

The 20:52 FINDING reported the coverage gap (291 of 544 calls over three days,
~53%) but explicitly gave no number for the second site: "I only measured the
open side; the second point has no measurement, so I report the coverage gap
and not a figure." This probe closes that.

It derives (workspace, scope, text) the way :805 does -- workspace from
`events[0]["workspace"]`, scope from `frame_scope(events)`, text from
`" ".join(str(v) for v in data.values())` of a real event's fields -- rather
than from CLI args the way :685 does. That argument derivation is the only
structural difference between the two sites; everything downstream is the same
`collapse_trace_registry(workspace, scope)`.

Nothing is written. `collapse_trace_registry` :4471 calls
`build_episode_index_value`, not `rebuild_episode_index`, so the rebuild branch
returns a value without touching the index file on disk.

Modes:
  --census   one process, no timing: how do real frames resolve under
             `frame_scope`, and how many :805-triggering events exist per scope
  (default)  one timed sample per process, matching the signed A/B discipline

Usage:
  python _probe_20260802_event_callsite_ab.py --script <path> --census
  python _probe_20260802_event_callsite_ab.py --script <path> [--memo] [--mem]
"""

import argparse
import collections
import hashlib
import importlib.util
import json
import pathlib
import sys
import time
import tracemalloc

WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
TRIGGERING_TYPES = ("candidate_admitted", "holder_selected", "route_reentered")


def load_trace(path):
    script_dir = str(pathlib.Path(path).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("weilan_trace_event_callsite", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame_files(wt):
    root = wt.state_root() / "frames"
    return sorted(root.glob("*/*.jsonl")) if root.exists() else []


def event_site_args(wt, events, data):
    """Reproduce weilan_trace.py:806-809 argument derivation verbatim."""
    return (
        events[0]["workspace"],
        wt.frame_scope(events),
        " ".join(str(value) for value in data.values()),
    )


def census(wt):
    """How do real frames resolve, and how much traffic does :805 carry?"""
    scope_counts = collections.Counter()
    triggering = collections.Counter()
    triggering_by_scope = collections.Counter()
    workspace_mismatch = 0
    unreadable = 0
    sample = None
    total = 0
    for path in frame_files(wt):
        total += 1
        try:
            events = wt.read_events(path)
        except (OSError, ValueError, RuntimeError):
            unreadable += 1
            continue
        if not events:
            continue
        resolved = wt.frame_scope(events)
        scope_counts[resolved] += 1
        if wt.normalized_workspace(events[0].get("workspace", "")) != wt.normalized_workspace(WORKSPACE):
            workspace_mismatch += 1
            continue
        for event in events[1:]:
            event_type = event.get("event_type")
            if event_type in TRIGGERING_TYPES:
                triggering[event_type] += 1
                triggering_by_scope[resolved] += 1
                if sample is None and event.get("data"):
                    workspace, scope, text = event_site_args(wt, events, event["data"])
                    sample = {
                        "frame_file": path.name,
                        "event_type": event_type,
                        "resolved_workspace": workspace,
                        "resolved_scope": scope,
                        "text_len": len(text),
                        "text_head": text[:120],
                    }
    open_site_scope = wt.normalize_scope(SCOPE)
    open_site_workspace = wt.canonical_workspace(WORKSPACE)
    return {
        "mode": "census",
        "frame_files_total": total,
        "frames_unreadable": unreadable,
        "frames_workspace_mismatch": workspace_mismatch,
        "frame_scope_distribution": dict(scope_counts.most_common()),
        "triggering_events_by_type": dict(triggering),
        "triggering_events_total": sum(triggering.values()),
        "triggering_events_by_resolved_scope": dict(triggering_by_scope.most_common()),
        "open_site_resolves_to": {
            "workspace": open_site_workspace,
            "scope": open_site_scope,
        },
        "first_triggering_event_sample": sample,
        "scope_pairs_identical": bool(
            sample
            and wt.canonical_workspace(sample["resolved_workspace"]) == open_site_workspace
            and sample["resolved_scope"] == open_site_scope
        ),
    }


def pick_sample_event(wt):
    """Newest frame carrying a :805-triggering event; its args drive the timing."""
    for path in reversed(frame_files(wt)):
        try:
            events = wt.read_events(path)
        except (OSError, ValueError, RuntimeError):
            continue
        if not events:
            continue
        if wt.normalized_workspace(events[0].get("workspace", "")) != wt.normalized_workspace(WORKSPACE):
            continue
        for event in events[1:]:
            if event.get("event_type") in TRIGGERING_TYPES and event.get("data"):
                return path, events, event
    return None, None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--census", action="store_true")
    parser.add_argument("--site", choices=("event", "open"), default="event")
    parser.add_argument("--memo", action="store_true")
    parser.add_argument("--mem", action="store_true")
    args = parser.parse_args()

    wt = load_trace(args.script)

    if args.census:
        print(json.dumps(census(wt), ensure_ascii=False))
        return

    path, events, event = pick_sample_event(wt)
    if event is None:
        raise SystemExit("no :805-triggering event found in this workspace's frames")
    if args.site == "event":
        workspace, scope, text = event_site_args(wt, events, event["data"])
    else:
        # weilan_trace.py:686 -- args.problem + args.success of the same frame,
        # with workspace/scope resolved from the CLI the way :646-647 does.
        opened = events[0].get("data", {})
        workspace = wt.canonical_workspace(WORKSPACE)
        scope = wt.normalize_scope(SCOPE)
        text = " ".join([str(opened.get("problem", "")), str(opened.get("success_criteria", ""))])

    builds = {"count": 0}
    real_build = wt.build_episode_index_value

    def counting_build(ws, sc):
        builds["count"] += 1
        return real_build(ws, sc)

    wt.build_episode_index_value = counting_build

    if args.mem:
        tracemalloc.start()
    output = {"frame_id": events[0]["frame_id"], "event_type": event["event_type"]}
    started = time.perf_counter()
    if args.memo:
        with wt.derivation_memo_scope():
            wt.attach_trace_advisory_result(output, workspace, scope, text)
    else:
        wt.attach_trace_advisory_result(output, workspace, scope, text)
    elapsed = time.perf_counter() - started

    payload = json.dumps(
        output, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    result = {
        "mode": "timed",
        "call_site": "command_event:805" if args.site == "event" else "command_open_lineaged_fenced:685",
        "arm": "candidate-memo" if args.memo else "baseline-nomemo",
        "index_state": "as-found",
        "build_episode_index_calls": builds["count"],
        "advisory_count": len(output.get("trace_advisories", [])),
        "advisory_error": output.get("trace_advisory_error", {}).get("error"),
        "advisory_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "seconds_callsite": round(elapsed, 3),
        "sample_frame_file": path.name,
        "sample_event_type": event["event_type"],
        "resolved_scope": scope,
        "text_len": len(text),
        "script": args.script,
    }
    if args.mem:
        _, peak = tracemalloc.get_traced_memory()
        result["peak_python_heap_mb"] = round(peak / 1e6, 1)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
