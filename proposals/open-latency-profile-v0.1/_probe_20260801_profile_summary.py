"""Summarise the sandboxed `open` profile: where the wall clock actually goes."""

import pstats
import sys

st = pstats.Stats(sys.argv[1])
total = st.total_tt
print(f"profiled_total_tt={total:.3f}s  primitive_calls={st.prim_calls}  calls={st.total_calls}")

print("\n=== top 18 by cumulative ===")
st.sort_stats("cumulative")
rows = []
for func, (cc, nc, tt, ct, callers) in st.stats.items():
    rows.append((ct, tt, nc, func))
rows.sort(reverse=True)
for ct, tt, nc, func in rows[:18]:
    fn, ln, name = func
    short = fn.split("\\")[-1]
    print(f"cum={ct:8.3f}  tot={tt:8.3f}  ncalls={nc:8d}  {short}:{ln}({name})")

print("\n=== top 18 by tottime (self) ===")
rows2 = sorted(((tt, ct, nc, f) for f, (cc, nc, tt, ct, cs) in st.stats.items()), reverse=True)
for tt, ct, nc, func in rows2[:18]:
    fn, ln, name = func
    short = fn.split("\\")[-1]
    print(f"tot={tt:8.3f}  cum={ct:8.3f}  ncalls={nc:8d}  {short}:{ln}({name})")

print("\n=== filesystem / io primitives ===")
keys = ("scandir", "stat", "lexists", "listdir", "open", "read", "glob",
        "loads", "fsync", "replace", "locking", "sleep")
agg = {}
for func, (cc, nc, tt, ct, cs) in st.stats.items():
    fn, ln, name = func
    low = name.lower()
    for k in keys:
        if k in low:
            a = agg.setdefault(k, [0.0, 0])
            a[0] += tt
            a[1] += nc
for k, (tt, nc) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"{k:12s} self={tt:8.3f}s  ncalls={nc}")
