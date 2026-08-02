"""Read-only probe: which memo keys hold the +34.2 MB the stop-line tripped on?

Context. The co-signed candidate (peer-chat 2026-08-02T15:59:34+09:00, agreed
16:33:55) wraps the whole advisory call site at the end of `open` in
`derivation_memo_scope()`. Review measured it on the as-found corpus: 0.499x
wall clock but +34.2 MB peak Python heap, which trips the acceptance item-4
stop line (+25 MB), so Codex ruled it unacceptable under the current signature
(peer-chat 2026-08-02T19:49:14+09:00).

In that review I floated one alternative without testing it: "narrow the memo
scope to cover only the freshness+build frame reads, avoiding the residency of
the governance/semantic tables". This probe exists to test that claim before
anyone writes a proposal on it, because if the bytes are in the frame reads
instead, that narrowing keeps the whole cost and drops the part that is free --
i.e. it would be exactly the wrong cut.

What it measures, per arm, one sample per process:
  * peak Python heap (tracemalloc) across the advisory call, same knob the
    signed acceptance item 4 uses;
  * for the memo arm only, the retained deep size of the memo dict at the
    moment the call returns, broken down by memo key class (key[0]), plus the
    entry count per class. Deep size walks dict/list/tuple/set/str/bytes with
    id-dedup, so shared objects are counted once.

Read-only: `build_episode_index_value` returns a value and never writes;
`rebuild_episode_index` is never called. Nothing is written to the ledger.

Caveats, written down so they are not read past:
  * tracemalloc peak counts Python allocation bytes, not RSS, and includes
    transient allocations; the retained-memo figure is a separate quantity and
    the two are not expected to be equal.
  * deep sizes come from sys.getsizeof, which is an implementation-defined
    approximation; use the shares between classes, not the absolute bytes.
  * every number covers the as-found method-state corpus at this instant on
    this one machine. The corpus only grows.

Usage (one sample per process):
  python _probe_20260802_memo_composition.py --script <path> [--memo]
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
    spec = importlib.util.spec_from_file_location("weilan_trace_memo_composition", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def deep_size(obj, seen):
    """Bytes reachable from obj, counting each distinct object at most once."""

    stack = [obj]
    total = 0
    while stack:
        item = stack.pop()
        marker = id(item)
        if marker in seen:
            continue
        seen.add(marker)
        total += sys.getsizeof(item)
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, (list, tuple, set, frozenset)):
            stack.extend(item)
    return total


def memo_breakdown(memo):
    """Per key-class entry count and retained deep bytes, id-deduped globally.

    The dedup set is shared across classes and the classes are visited in a
    fixed sorted order, so an object reachable from two classes is charged to
    the first one visited. Any such sharing is reported in `note`.
    """

    classes = {}
    for key in memo:
        name = key[0] if isinstance(key, tuple) and key else str(type(key))
        classes.setdefault(name, []).append(key)
    seen = set()
    rows = []
    for name in sorted(classes):
        keys = classes[name]
        before = len(seen)
        size = sum(deep_size(memo[key], seen) for key in keys)
        rows.append({
            "key_class": name,
            "entries": len(keys),
            "retained_bytes": size,
            "retained_mb": round(size / 1e6, 2),
            "distinct_objects": len(seen) - before,
        })
    total = sum(row["retained_bytes"] for row in rows)
    for row in rows:
        row["share_of_retained"] = round(row["retained_bytes"] / total, 4) if total else None
    return rows, total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--memo", action="store_true")
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

    output = {}
    breakdown = None
    retained_total = None
    tracemalloc.start()
    started = time.perf_counter()
    if args.memo:
        with wt.derivation_memo_scope():
            wt.attach_trace_advisory_result(output, workspace, scope, args.text)
            elapsed = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
            memo = wt._DERIVATION_MEMO.get()
            breakdown, retained_total = memo_breakdown(memo)
    else:
        wt.attach_trace_advisory_result(output, workspace, scope, args.text)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()

    payload = json.dumps(
        output, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    result = {
        "arm": "candidate-memo" if args.memo else "baseline-nomemo",
        "index_state": "as-found",
        "build_episode_index_calls": builds["count"],
        "advisory_count": len(output.get("trace_advisories", [])),
        "advisory_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "seconds_callsite": round(elapsed, 3),
        "peak_python_heap_mb": round(peak / 1e6, 1),
        "script": args.script,
    }
    if breakdown is not None:
        result["memo_retained_mb"] = round(retained_total / 1e6, 2)
        result["memo_entries"] = sum(row["entries"] for row in breakdown)
        result["memo_by_key_class"] = breakdown
        result["note"] = (
            "retained = deep size of the memo dict at call return, id-deduped "
            "across classes in sorted class order; peak = tracemalloc, includes "
            "transient allocations and is not RSS"
        )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
