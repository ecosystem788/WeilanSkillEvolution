"""Read-only review probe: exercise the SIGNED call site (attach_trace_advisory_result)
under base vs candidate weilan_trace.py, in a fresh process each, and emit a canonical
digest of the advisory-bearing output keys plus wall clock.

Why this exists: the delegated A/B (_probe_20260802_advisory_ab.py) wraps
episode_index_is_fresh + build_episode_index_value directly. That is a sub-segment of
collapse_trace_registry and omits reduce_governance, so it does not measure the call
site the co-signature named. This probe calls the named function itself.

Usage (one arm per process):
  python _probe_20260802_review_advisory_callsite.py --script <path> --workspace <ws> --scope <scope>

Writes nothing. Reads only.
"""

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
import time


def load_trace(path):
    script_dir = str(pathlib.Path(path).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("weilan_trace_review_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--memo", action="store_true")
    parser.add_argument(
        "--text",
        default="bounded review of the open advisory memo wrapper candidate",
        help="stands in for ' '.join([args.problem, args.success]) at the call site",
    )
    args = parser.parse_args()

    wt = load_trace(args.script)
    workspace = wt.canonical_workspace(args.workspace)
    scope = wt.normalize_scope(args.scope)

    output = {}
    started = time.perf_counter()
    if args.memo:
        with wt.derivation_memo_scope():
            wt.attach_trace_advisory_result(output, workspace, scope, args.text)
    else:
        wt.attach_trace_advisory_result(output, workspace, scope, args.text)
    elapsed = time.perf_counter() - started

    payload = json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    print(json.dumps({
        "script": str(pathlib.Path(args.script).resolve()),
        "script_sha256": hashlib.sha256(pathlib.Path(args.script).read_bytes()).hexdigest(),
        "runtime_core_sha256": hashlib.sha256(
            (pathlib.Path(args.script).resolve().parent / "runtime_core.py").read_bytes()
        ).hexdigest(),
        "memo_wrapper_applied_by_probe": bool(args.memo),
        "advisory_keys": sorted(output.keys()),
        "advisory_payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "advisory_payload_len": len(payload),
        "seconds_callsite": round(elapsed, 3),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
