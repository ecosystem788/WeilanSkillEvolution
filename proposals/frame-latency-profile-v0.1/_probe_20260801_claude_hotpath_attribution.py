"""Read-only cProfile attribution for the slowest weilan_trace read path.

The bucket ladder (_probe_20260801_claude_latency_buckets) located the cost:
interpreter startup + import + parser build together are ~0.29s, while the
`lineage-show` command body alone is ~34s. This probe opens that 34s and
attributes it to functions.

Method: run the real CLI under cProfile in a subprocess, then read the stats
file. `command_lineage_show` is read-only (it loads lineage records, replays
frame events, and prints); no ledger row is written by this probe. Only this
probe's own .out.json and a .prof file next to it are created.

Boundary: cProfile adds per-call overhead, so absolute seconds here run higher
than the uninstrumented 34s. Read the SHARES, not the absolute totals; the
uninstrumented number of record is in the bucket-ladder probe.
"""

import cProfile  # noqa: F401  (documents intent; profiling runs in a subprocess)
import json
import pstats
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py")
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
PROF = HERE / "_probe_20260801_claude_hotpath_attribution.prof"


def run_profiled():
    argv = [
        sys.executable,
        "-m",
        "cProfile",
        "-o",
        str(PROF),
        str(TRACE),
        "lineage-show",
        "--workspace",
        WORKSPACE,
        "--scope",
        SCOPE,
    ]
    proc = subprocess.run(argv, capture_output=True)
    return {"rc": proc.returncode, "stdout_bytes": len(proc.stdout), "stderr_tail": proc.stderr.decode("utf-8", "replace")[-400:]}


def top_functions(stats, n=25, sort="cumulative"):
    stats.sort_stats(sort)
    rows = []
    for func, (cc, nc, tt, ct, _callers) in list(stats.stats.items()):
        rows.append(
            {
                "func": "{}:{}({})".format(Path(func[0]).name, func[1], func[2]),
                "ncalls": nc,
                "primitive_calls": cc,
                "tottime_s": round(tt, 4),
                "cumtime_s": round(ct, 4),
            }
        )
    key = "cumtime_s" if sort == "cumulative" else "tottime_s"
    rows.sort(key=lambda r: r[key], reverse=True)
    return rows[:n]


def main():
    result = {"probe": "hotpath_attribution", "boundary": __doc__.strip().splitlines()[-2:]}
    result["profiled_run"] = run_profiled()
    if result["profiled_run"]["rc"] != 0 or not PROF.exists():
        result["error"] = "profiled run failed; no attribution produced"
        (HERE / (Path(__file__).stem + ".out.json")).write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 1

    stats = pstats.Stats(str(PROF))
    result["total_profiled_s"] = round(stats.total_tt, 4)
    result["total_calls"] = stats.total_calls
    result["by_cumulative"] = top_functions(stats, 25, "cumulative")
    result["by_tottime"] = top_functions(stats, 25, "tottime")

    # Named suspects: attribute the syscall-level work explicitly.
    suspects = {}
    for func, (cc, nc, tt, ct, _callers) in stats.stats.items():
        name = "{}:{}".format(Path(func[0]).name, func[2])
        for tag in ("find_frame", "glob", "scandir", "listdir", "read_events", "load_lineage_records", "json.loads", "loads", "stat", "open"):
            if tag in func[2] or tag in name:
                suspects.setdefault(tag, []).append(
                    {"func": "{}:{}({})".format(Path(func[0]).name, func[1], func[2]),
                     "ncalls": nc, "tottime_s": round(tt, 4), "cumtime_s": round(ct, 4)}
                )
    for tag in suspects:
        suspects[tag].sort(key=lambda r: r["cumtime_s"], reverse=True)
        suspects[tag] = suspects[tag][:5]
    result["named_suspects"] = suspects

    out = HERE / (Path(__file__).stem + ".out.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    print("total profiled tottime_s:", result["total_profiled_s"], "calls:", result["total_calls"])
    print("\n-- top 12 by cumulative --")
    for row in result["by_cumulative"][:12]:
        print("  {cumtime_s:>10}  {tottime_s:>10}  {ncalls:>9}  {func}".format(**row))
    print("\n-- top 12 by tottime --")
    for row in result["by_tottime"][:12]:
        print("  {tottime_s:>10}  {ncalls:>9}  {func}".format(**row))
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
