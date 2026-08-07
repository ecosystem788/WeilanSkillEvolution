#!/usr/bin/env python3
"""Read-only follow-up: is the self-report run's 19.6% shortfall typical FOR
ITS KIND, or is it an outlier I generalised?

Probe 1 showed median shortfall across all 1927 runs = 2.0%, but a
self-reporting run is not a random run: peer-chat:3574 section 2 argues it is
systematically a deep-audit-and-write-up run, and those are expensive.  So the
honest comparison group is "deep runs", not "all runs".

Proxy for depth = turns.  turns is emitted by the tooling, not hand-written,
so it is not exposed to the ledger-timestamp hand-writing problem that would
poison any peer-chat `time` -> run mapping.

Writes nothing.
"""
import io
import os
import re
import statistics
from collections import defaultdict

def _repo_root(start):
    """Walk up to the directory that actually contains proposals/ -- so the
    probe reruns from evidence/ or from anywhere else it gets copied."""
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, "proposals")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit("repo root (a dir containing proposals/) not found")
        d = parent


ROOT = _repo_root(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl/wake-agent.log")

LINE = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})\s+"
    r"rc=(?P<rc>-?\d+)\s+(?P<status>\S+)\s+turns=(?P<turns>\d+)\s+"
    r"cost=\$(?P<cost>[0-9.]+)\b"
)

rows = []
for raw in io.open(LOG, encoding="utf-8-sig").read().splitlines():
    m = LINE.match(raw.strip())
    if not m:
        continue
    rows.append({
        "stamp": m.group("stamp"),
        "day": m.group("stamp")[:10],
        "rc": int(m.group("rc")),
        "turns": int(m.group("turns")),
        "cost": float(m.group("cost")),
    })
rows.sort(key=lambda r: r["stamp"])

by_day = defaultdict(list)
for r in rows:
    by_day[r["day"]].append(r)
for day, drs in by_day.items():
    running = 0.0
    for r in drs:
        running += r["cost"]
        r["truth"] = running
        r["shortfall"] = r["cost"] / running if running > 0 else None

# Drop the degenerate first-run-of-day (shortfall 100% by construction) and
# zero-cost failed runs -- a failed run cannot write a self-report.
usable = [r for r in rows
          if r["shortfall"] is not None
          and by_day[r["day"]][0]["stamp"] != r["stamp"]
          and r["cost"] > 0]
print(f"usable runs (non-first-of-day, cost>0): {len(usable)}")

turns = sorted(r["turns"] for r in usable)
def q(vals, p):
    s = sorted(vals)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)

print(f"turns distribution: median {statistics.median(turns)}  "
      f"p75 {q(turns,.75):.0f}  p90 {q(turns,.90):.0f}  p99 {q(turns,.99):.0f}  max {max(turns)}")

print()
print("== shortfall stratified by turns (depth proxy) ==")
print(f"{'bucket':<18}{'n':>6}{'med turns':>11}{'med cost$':>11}{'med shortfall':>15}{'p90 shortfall':>15}")
buckets = [
    ("turns <= 20", lambda t: t <= 20),
    ("21-40", lambda t: 21 <= t <= 40),
    ("41-60", lambda t: 41 <= t <= 60),
    ("61-80", lambda t: 61 <= t <= 80),
    ("turns > 80", lambda t: t > 80),
]
for name, pred in buckets:
    grp = [r for r in usable if pred(r["turns"])]
    if not grp:
        print(f"{name:<18}{0:>6}")
        continue
    sf = [r["shortfall"] for r in grp]
    print(f"{name:<18}{len(grp):>6}{statistics.median([r['turns'] for r in grp]):>11.0f}"
          f"{statistics.median([r['cost'] for r in grp]):>11.4f}"
          f"{statistics.median(sf):>14.1%}{q(sf,.90):>15.1%}")

# The self-report run had turns=68.  What does its own stratum look like?
print()
print("== the comparison group that actually matters ==")
print("   the identified self-report run: turns=68, cost=$20.8998, shortfall=19.6%")
peer = [r for r in usable if 61 <= r["turns"] <= 80]
if peer:
    sf = [r["shortfall"] for r in peer]
    cs = [r["cost"] for r in peer]
    print(f"   its stratum (61-80 turns): n={len(peer)}")
    print(f"     shortfall  median {statistics.median(sf):.1%}  p90 {q(sf,.90):.1%}  max {max(sf):.1%}")
    print(f"     cost       median ${statistics.median(cs):.2f}  max ${max(cs):.2f}")
    worse = sum(1 for x in sf if x >= 0.196)
    print(f"     runs in this stratum with shortfall >= 19.6%: {worse}/{len(peer)} = {worse/len(peer):.1%}")

# Does high turns even predict high shortfall?  Shortfall depends on cost
# relative to the whole day, so a big day dilutes it regardless of depth.
print()
print("== does depth predict shortfall at all? ==")
hi = [r["shortfall"] for r in usable if r["turns"] > q(turns, .90)]
lo = [r["shortfall"] for r in usable if r["turns"] <= statistics.median(turns)]
print(f"   turns > p90 ({q(turns,.90):.0f}): n={len(hi)} median shortfall {statistics.median(hi):.1%}")
print(f"   turns <= median      : n={len(lo)} median shortfall {statistics.median(lo):.1%}")
print(f"   ratio of medians     : {statistics.median(hi)/statistics.median(lo):.1f}x")

# And how rare is 19.6% overall?
allsf = sorted(r["shortfall"] for r in usable)
rank = sum(1 for x in allsf if x < 0.196)
print()
print(f"== where 19.6% sits among all {len(allsf)} usable runs ==")
print(f"   percentile: {rank/len(allsf):.1%}  "
      f"(i.e. {len(allsf)-rank} runs, {(len(allsf)-rank)/len(allsf):.1%}, are at least that bad)")

# The 2026-08-07 day specifically -- the day the $85.83 report covered.
print()
print("== 2026-08-07 alone (the day of the report given to the observer) ==")
d = [r for r in by_day["2026-08-07"] if r["cost"] > 0]
sf = [r["shortfall"] for r in d if r["shortfall"] is not None]
print(f"   runs cost>0: {len(d)}  median shortfall {statistics.median(sf):.1%}  max {max(sf):.1%}")
print(f"   cost: median ${statistics.median([r['cost'] for r in d]):.2f}  max ${max([r['cost'] for r in d]):.2f}  sum ${sum(r['cost'] for r in d):.2f}")
top = sorted(d, key=lambda r: -r["cost"])[:5]
print("   top 5 by cost:")
for r in top:
    print(f"     {r['stamp']}  turns={r['turns']:>3}  ${r['cost']:>8.4f}  shortfall={r['shortfall']:.1%}")
