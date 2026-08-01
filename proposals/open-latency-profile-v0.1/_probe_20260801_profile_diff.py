"""Baseline-vs-candidate `open` profile diff, restricted to the functions that moved."""

import json
import pstats
import sys


def load(path):
    st = pstats.Stats(path)
    out = {}
    for (fn, ln, name), (cc, nc, tt, ct, cs) in st.stats.items():
        out[f"{fn.split(chr(92))[-1]}:{ln}({name})"] = {"ncalls": nc, "self": tt, "cum": ct}
    return st.total_tt, out


base_total, base = load(sys.argv[1])
cand_total, cand = load(sys.argv[2])

WATCH = [
    "weilan_trace.py:4551(attach_trace_advisory_result)",
    "weilan_trace.py:4458(collapse_trace_registry)",
    "weilan_trace.py:6439(build_episode_index_value)",
    "weilan_trace.py:6476(episode_index_is_fresh)",
    "weilan_trace.py:6315(scan)",
    "weilan_trace.py:304(read_events)",
    "runtime_core.py:26(canonical_workspace)",
    "~:0(<built-in method nt._getfinalpathname>)",
    "~:0(<built-in method nt.stat>)",
    "~:0(<built-in method io.open>)",
]

report = {
    "profiled_total_tt": {"baseline": round(base_total, 3), "candidate": round(cand_total, 3)},
    "note": "cProfile inflates wall clock; unprofiled warm means were baseline 34.650s / candidate 15.022s",
    "functions": {},
}
for key in WATCH:
    b = base.get(key, {"ncalls": 0, "self": 0.0, "cum": 0.0})
    c = cand.get(key, {"ncalls": 0, "self": 0.0, "cum": 0.0})
    report["functions"][key] = {
        "baseline": {"ncalls": b["ncalls"], "self_s": round(b["self"], 3), "cum_s": round(b["cum"], 3)},
        "candidate": {"ncalls": c["ncalls"], "self_s": round(c["self"], 3), "cum_s": round(c["cum"], 3)},
        "self_delta_s": round(c["self"] - b["self"], 3),
        "ncalls_delta": c["ncalls"] - b["ncalls"],
    }

print(json.dumps(report, ensure_ascii=False, indent=2))
