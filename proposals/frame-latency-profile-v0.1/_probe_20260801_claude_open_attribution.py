"""Attribute the cost of a REAL `weilan_trace open` call, under cProfile.

The bucket ladder measured the CLI's read paths. `open` is a write path and
cannot be measured without writing, so this probe does not create an extra
frame: it wraps the one frame this turn has to open for its receipt anyway.
The frame is real, the profile is of that real call.

Boundary: cProfile inflates absolute seconds (the uninstrumented `open` of the
previous turn was 30.06s, archived in find-frame-index-v0.1/
_probe_20260801_claude_predeploy_latency.out.json). Read the SHARES.
"""

import json
import pstats
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py")
PROF = HERE / "_probe_20260801_claude_open_attribution.prof"

# The projection's source_snapshots head (wf-20260801-013657-8c700c) was already
# stale at recall time; the live branch head reported by the rejected open is used.
PARENT = "wf-20260801-014615-bb5ed7"
PROBLEM = (
    "Observer directive peer-chat 3248 item 3: bucketed profiling of the per-turn "
    "receipt-chain latency, after the find-frame-index adoption package was rejected."
)
SUCCESS = (
    "A read-only bucket ladder plus function-level attribution that names where the "
    "seconds go, with call counts, archived as probe output."
)


def main():
    argv = [
        sys.executable, "-m", "cProfile", "-o", str(PROF), str(TRACE), "open",
        "--level", "L2",
        "--problem", PROBLEM,
        "--success", SUCCESS,
        "--budget", "one bounded turn",
        "--workspace", r"D:\WeilanSkillEvolution",
        "--scope", "skill-evolution",
        "--branch", "main",
        "--relation", "continue",
        "--parent", PARENT,
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(argv, capture_output=True)
    elapsed = round(time.perf_counter() - t0, 3)

    result = {
        "probe": "open_attribution",
        "elapsed_s_profiled": elapsed,
        "rc": proc.returncode,
        "stdout": proc.stdout.decode("utf-8", "replace"),
        "stderr_tail": proc.stderr.decode("utf-8", "replace")[-800:],
        "boundary": __doc__.strip().splitlines()[-2:],
    }

    if PROF.exists():
        stats = pstats.Stats(str(PROF))
        result["total_profiled_s"] = round(stats.total_tt, 4)
        result["total_calls"] = stats.total_calls
        rows = []
        for func, (cc, nc, tt, ct, _c) in stats.stats.items():
            rows.append({
                "func": "{}:{}({})".format(Path(func[0]).name, func[1], func[2]),
                "ncalls": nc, "tottime_s": round(tt, 4), "cumtime_s": round(ct, 4),
            })
        result["by_cumulative"] = sorted(rows, key=lambda r: r["cumtime_s"], reverse=True)[:25]
        result["by_tottime"] = sorted(rows, key=lambda r: r["tottime_s"], reverse=True)[:15]
        result["find_frame"] = [r for r in rows if "find_frame" in r["func"]]
        result["nt_stat"] = [r for r in rows if "nt.stat" in r["func"]]

    out = HERE / (Path(__file__).stem + ".out.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print("rc", result["rc"], "elapsed_s", elapsed)
    print(result["stdout"][:600])
    print(result["stderr_tail"][-300:])
    for row in result.get("by_cumulative", [])[:12]:
        print("  {cumtime_s:>10} {tottime_s:>10} {ncalls:>9}  {func}".format(**row))
    print("find_frame:", json.dumps(result.get("find_frame"), ensure_ascii=False))
    print("nt.stat:", json.dumps(result.get("nt_stat"), ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
