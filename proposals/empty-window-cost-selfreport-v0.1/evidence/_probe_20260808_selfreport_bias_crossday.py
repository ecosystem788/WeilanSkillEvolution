#!/usr/bin/env python3
"""Read-only: cross-day quantification of the self-report cost under-count.

Closes the n=1 hole I left in peer-chat:3574 section 6 item 4
("the missed one is usually a larger one" -- only one sample).

Writes nothing. Reads only wake-agent.log.

Structural fact being measured (wake_agent.ps1:14 $stamp=Get-Date at run
start, :323 wait-for-exit, :339 Add-Content): a log line exists only AFTER
its run ends, so a model turn running inside that process can never see its
own entry.  Therefore ANY in-run self-report of "today's cost" omits exactly
one line: its own.

(A) is computable for every run without knowing which runs actually
self-reported: treat each run r as a hypothetical self-reporter and compute
    reported(r)  = sum of same-day costs strictly before r's stamp
    truth(r)     = reported(r) + cost(r)
    shortfall(r) = cost(r) / truth(r)
(B) needs the real self-report runs; only one is known, so it stays flagged.
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

# BOM: the log starts with U+FEFF -- utf-8-sig, not utf-8.
LINE = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})\s+"
    r"rc=(?P<rc>-?\d+)\s+(?P<status>\S+)\s+turns=(?P<turns>\d+)\s+"
    r"cost=\$(?P<cost>[0-9.]+)\b"
)

rows = []
unparsed = 0
nonnumeric_cost = 0
total_lines = 0
for raw in io.open(LOG, encoding="utf-8-sig", errors="strict").read().splitlines():
    raw = raw.strip()
    if not raw:
        continue
    total_lines += 1
    m = LINE.match(raw)
    if not m:
        # distinguish the two known non-parse classes rather than lumping them
        if "cost=$?" in raw:
            nonnumeric_cost += 1
        else:
            unparsed += 1
        continue
    stamp = m.group("stamp")
    rows.append({
        "stamp": stamp,
        "day": stamp[:10],
        "rc": int(m.group("rc")),
        "turns": int(m.group("turns")),
        "cost": float(m.group("cost")),
    })

rows.sort(key=lambda r: r["stamp"])
print("== parse ==")
print(f"total non-empty lines : {total_lines}")
print(f"parsed with numeric $ : {len(rows)}")
print(f"cost=$? (literal)     : {nonnumeric_cost}")
print(f"other unparsed        : {unparsed}")
print(f"span                  : {rows[0]['stamp']} .. {rows[-1]['stamp']}")

by_day = defaultdict(list)
for r in rows:
    by_day[r["day"]].append(r)

# ---- (A) hypothetical-self-reporter shortfall, every run, every day ----
print()
print("== (A) shortfall if THIS run had self-reported, all runs ==")
short = []
for day, drs in sorted(by_day.items()):
    running = 0.0
    for r in drs:
        reported = running
        running += r["cost"]
        truth = running
        if truth <= 0:
            continue
        r["shortfall"] = r["cost"] / truth
        r["reported"] = reported
        r["truth"] = truth
        short.append(r["shortfall"])

short_sorted = sorted(short)
def pct(p):
    if not short_sorted:
        return float("nan")
    k = (len(short_sorted) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(short_sorted) - 1)
    return short_sorted[lo] + (short_sorted[hi] - short_sorted[lo]) * (k - lo)

print(f"n runs with defined shortfall : {len(short)}")
print(f"median shortfall              : {statistics.median(short):.1%}")
print(f"mean shortfall                : {statistics.fmean(short):.1%}")
print(f"p10 / p25 / p75 / p90         : {pct(.10):.1%} / {pct(.25):.1%} / {pct(.75):.1%} / {pct(.90):.1%}")
print(f"min / max                     : {min(short):.1%} / {max(short):.1%}")

# how much of the mass is the trivial "first run of the day = 100%" artifact
first_of_day = {d: drs[0]["stamp"] for d, drs in by_day.items()}
firsts = [r["shortfall"] for r in rows if r.get("shortfall") is not None and first_of_day.get(r["day"]) == r["stamp"]]
rest = [r["shortfall"] for r in rows if r.get("shortfall") is not None and first_of_day.get(r["day"]) != r["stamp"]]
print(f"  of which first-run-of-day   : n={len(firsts)} (shortfall is 100% by construction)")
print(f"  excluding first-run-of-day  : n={len(rest)} median {statistics.median(rest):.1%} mean {statistics.fmean(rest):.1%}")

# ---- shortfall late in the day, where a real self-report would sit ----
print()
print("== (A2) same, restricted to runs in the LAST QUARTER of each day's runs ==")
print("   (a self-report summarising 'today' is written late, not at 00:05)")
late = []
for day, drs in sorted(by_day.items()):
    cut = int(len(drs) * 0.75)
    for r in drs[cut:]:
        if r.get("shortfall") is not None:
            late.append(r["shortfall"])
if late:
    print(f"n={len(late)} median {statistics.median(late):.1%} mean {statistics.fmean(late):.1%} max {max(late):.1%}")

# ---- (B) is the omitted run a LARGER-than-typical one? ----
print()
print("== (B) is a run's own cost above its day's median? (the 3574 claim) ==")
print("   Answered here for ALL runs as a base rate, since only one true")
print("   self-report run is identified.  A base rate near 50% would mean")
print("   'the missed one is usually a larger one' has NO support beyond")
print("   the specific run; a high rate among late runs would support it.")
above_all = 0
n_all = 0
above_late = 0
n_late = 0
for day, drs in sorted(by_day.items()):
    if len(drs) < 4:
        continue
    med = statistics.median([r["cost"] for r in drs])
    cut = int(len(drs) * 0.75)
    for i, r in enumerate(drs):
        n_all += 1
        if r["cost"] > med:
            above_all += 1
        if i >= cut:
            n_late += 1
            if r["cost"] > med:
                above_late += 1
print(f"all runs   : {above_all}/{n_all} = {above_all/n_all:.1%} above same-day median")
print(f"late runs  : {above_late}/{n_late} = {above_late/n_late:.1%} above same-day median")

# ---- the one known real self-report run ----
print()
print("== the single identified real self-report run (3564, 2026-08-07T17-56-27) ==")
target = "2026-08-07T17-56-27"
for r in rows:
    if r["stamp"] == target:
        day = by_day[r["day"]]
        med = statistics.median([x["cost"] for x in day])
        rank = sorted([x["cost"] for x in day], reverse=True).index(r["cost"]) + 1
        print(f"cost=${r['cost']:.4f} turns={r['turns']}")
        print(f"day median=${med:.4f}  -> {r['cost']/med:.2f}x median")
        print(f"rank within day by cost: {rank} of {len(day)}")
        print(f"reported=${r['reported']:.2f}  truth=${r['truth']:.2f}  shortfall={r['shortfall']:.1%}")
        break
else:
    print("NOT FOUND -- do not read the rest as covering it")

# ---- per-day table so the numbers are auditable, not just summarised ----
print()
print("== per-day (auditable) ==")
print(f"{'day':<12}{'runs':>5}{'sum$':>10}{'median$':>10}{'max$':>10}{'lastrun_shortfall':>20}")
for day, drs in sorted(by_day.items()):
    costs = [r["cost"] for r in drs]
    last = drs[-1]
    sf = f"{last['shortfall']:.1%}" if last.get("shortfall") is not None else "n/a"
    print(f"{day:<12}{len(drs):>5}{sum(costs):>10.2f}{statistics.median(costs):>10.4f}{max(costs):>10.4f}{sf:>20}")
