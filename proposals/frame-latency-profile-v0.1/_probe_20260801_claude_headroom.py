"""Read-only headroom measurement for the two costs the attribution named.

Nothing is deployed and no skill file is touched. Both measurements re-implement
the deployed code's call shape locally, at the call counts the cProfile run
actually recorded, so the numbers are "what this many calls cost on this host",
not "what a patch would achieve".

Cost A -- uncached path canonicalization. runtime_core.canonical_workspace does
Path(expandvars(expanduser(v))).resolve() on every call; the profile recorded
37,327 calls during one `open`, over a tiny set of distinct inputs.

Cost B -- whole-store frame rescan. scoped_frame_paths.scan() globs
frames/*/*.jsonl and read_events() every file to filter by workspace+scope;
collapse_trace_registry triggers it for the freshness check and again for the
index rebuild.
"""

import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = r"D:\WeilanSkillEvolution"
CALLS = 37327  # observed canonical_workspace call count in one profiled `open`


def canonical_workspace(value):
    """Verbatim copy of runtime_core.canonical_workspace (deployed, untouched)."""
    expanded = os.path.expandvars(os.path.expanduser(value))
    return str(Path(expanded).resolve())


def cached_factory():
    cache = {}

    def cached(value):
        hit = cache.get(value)
        if hit is None:
            hit = canonical_workspace(value)
            cache[value] = hit
        return hit

    return cached, cache


def bench(fn, n):
    t0 = time.perf_counter()
    for _ in range(n):
        fn(WORKSPACE)
    return round(time.perf_counter() - t0, 4)


def main():
    result = {"probe": "headroom", "observed_call_count": CALLS, "workspace": WORKSPACE}

    # Cost A, at the observed call count. Warm the OS path cache first so this is
    # not measuring a cold-start artefact.
    bench(canonical_workspace, 200)
    uncached_s = bench(canonical_workspace, CALLS)
    cached_fn, cache = cached_factory()
    cached_s = bench(cached_fn, CALLS)
    result["cost_a_path_canonicalization"] = {
        "uncached_s": uncached_s,
        "dict_cached_s": cached_s,
        "recoverable_s": round(uncached_s - cached_s, 4),
        "distinct_inputs_in_this_bench": len(cache),
        "note": "single-string bench; the deployed call sites pass a small set of distinct workspaces, so real distinct-key count is small but was not enumerated here",
    }

    # Cost B: how much data the whole-store rescan touches, per scan.
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    frames_root = Path(home) / "method-state" / "frames"
    files = 0
    total_bytes = 0
    dirs = 0
    if frames_root.exists():
        dirs = sum(1 for p in frames_root.iterdir() if p.is_dir())
        t0 = time.perf_counter()
        for path in sorted(frames_root.glob("*/*.jsonl")):
            files += 1
            try:
                total_bytes += path.stat().st_size
            except OSError:
                pass
        glob_s = round(time.perf_counter() - t0, 4)
        t0 = time.perf_counter()
        read_bytes = 0
        for path in frames_root.glob("*/*.jsonl"):
            try:
                read_bytes += len(path.read_bytes())
            except OSError:
                pass
        read_s = round(time.perf_counter() - t0, 4)
    else:
        glob_s = read_s = read_bytes = 0.0
    result["cost_b_whole_store_rescan"] = {
        "frames_root": str(frames_root),
        "date_dir_count": dirs,
        "frame_file_count": files,
        "total_bytes": total_bytes,
        "glob_plus_stat_s": glob_s,
        "read_every_file_s": read_s,
        "read_bytes": read_bytes,
        "note": "collapse_trace_registry walks this set twice per `open` (freshness check, then index rebuild), and read_events parses each line as JSON on top of the raw read measured here",
    }

    out = HERE / (Path(__file__).stem + ".out.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
