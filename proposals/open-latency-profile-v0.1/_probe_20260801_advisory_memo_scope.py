"""Read-only: does the open-path advisory pay the frame corpus scan more than once?

`command_open_lineaged` calls `assert_guarded_write_entry_outside_derivation_memo()`,
so the whole open runs with `_DERIVATION_MEMO` unset. `memoized_value` then degrades
to a plain call, which means every `scoped_frame_paths` / `read_events` inside
`attach_trace_advisory_result` re-reads the corpus from disk.

This probe times the two calls the advisory actually makes
(`episode_index_is_fresh` + `build_episode_index_value`) in the two shapes:

  arm=nomemo    : exactly today's open path (no memo scope)
  arm=memo      : the same two calls wrapped in `derivation_memo_scope()`
  arm=buildonly : inside a memo scope, the freshness call skipped entirely -- the
                  ceiling of "the freshness check becomes free" (the 2026-08-01
                  candidate 乙 shape) once a memo scope exists, i.e. what the build
                  costs when it has to pay the corpus read itself.

Both arms are pure reads: `build_episode_index_value` returns a value and never
writes; `rebuild_episode_index` (the writing one) is not called. Nothing under
`state_root()` is modified.

Usage: python _probe_20260801_advisory_memo_scope.py --arm nomemo|memo [--mem]
"""

import argparse
import json
import sys
import time

sys.path.insert(0, r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
import weilan_trace as wt  # noqa: E402

WS_ARG = r"D:\WeilanSkillEvolution"
SCOPE_ARG = "skill-evolution"


def advisory_core(workspace, scope, skip_freshness=False):
    """The two calls collapse_trace_registry makes, timed separately."""
    out = {}
    index = wt.load_episode_index(workspace, scope)
    t0 = time.perf_counter()
    if skip_freshness:
        fresh = False
        out["freshness_skipped"] = True
    else:
        fresh = wt.episode_index_is_fresh(index, workspace, scope)
    t1 = time.perf_counter()
    out["fresh"] = bool(fresh)
    out["seconds_freshness"] = round(t1 - t0, 3)
    if not fresh:
        value = wt.build_episode_index_value(workspace, scope)
        out["episode_count"] = value.get("episode_count")
    t2 = time.perf_counter()
    out["seconds_build"] = round(t2 - t1, 3)
    out["seconds_total"] = round(t2 - t0, 3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["nomemo", "memo", "buildonly"], required=True)
    ap.add_argument("--mem", action="store_true", help="measure peak python heap (distorts timing)")
    args = ap.parse_args()

    workspace = wt.canonical_workspace(WS_ARG)
    scope = wt.normalize_scope(SCOPE_ARG)

    if args.mem:
        import tracemalloc
        tracemalloc.start()

    if args.arm in ("memo", "buildonly"):
        with wt.derivation_memo_scope():
            result = advisory_core(workspace, scope, skip_freshness=args.arm == "buildonly")
    else:
        assert wt._DERIVATION_MEMO.get() is None, "expected no memo scope in the nomemo arm"
        result = advisory_core(workspace, scope)

    result["arm"] = args.arm
    if args.mem:
        import tracemalloc
        current, peak = tracemalloc.get_traced_memory()
        result["peak_python_heap_mb"] = round(peak / 1e6, 1)
        tracemalloc.stop()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
