import io, os, re, json, subprocess
from datetime import datetime, timedelta, timezone

ROOT = r"D:/WeilanSkillEvolution"
LOG = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl/wake-agent.log")
JST = timezone(timedelta(hours=9))
LINE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})\s+rc=(?P<rc>-?\d+)\s+(?P<status>\S+)"
    r"(?:\s+turns=(?P<turns>\d+))?(?:\s+cost=\$(?P<cost>[\d.]+))?(?P<rest>.*)$")

rows = []
for raw in io.open(LOG, encoding="utf-8", errors="replace").read().splitlines():
    s = raw.strip().lstrip("\ufeff")
    if not s:
        continue
    m = LINE.match(s)
    if not m:
        continue
    rows.append({"ts": datetime.strptime(m.group("ts"), "%Y-%m-%dT%H-%M-%S").replace(tzinfo=JST),
                 "turns": int(m.group("turns")) if m.group("turns") else None,
                 "cost": float(m.group("cost")) if m.group("cost") else None,
                 "raw": s})

day0 = datetime(2026, 8, 7, 0, 0, tzinfo=JST)
cut = datetime(2026, 8, 7, 18, 12, 19, tzinfo=JST)
inflight = datetime(2026, 8, 7, 17, 56, 27, tzinfo=JST)

print("=== Q1: does excluding the in-flight 17:56:27 row reproduce 38 / $85.83? ===")
completed = [r for r in rows if day0 <= r["ts"] < inflight and r["cost"] is not None]
print("  rows strictly before 17:56:27 today: n=%d  cost=$%.2f" % (
    len(completed), sum(r["cost"] for r in completed)))
row1756 = [r for r in rows if r["ts"] == inflight]
for r in row1756:
    print("  the 17:56:27 row itself: turns=%s cost=$%.4f" % (r["turns"], r["cost"]))
print("  3564 asserted: n=38 cost=$85.83")

print("\n=== Q2: when do zero-cost rows occur? ===")
z = [r for r in rows if r["cost"] == 0.0]
print("  zero-cost rows:", len(z))
if z:
    print("  first:", z[0]["ts"].isoformat(), " last:", z[-1]["ts"].isoformat())
    byday = {}
    for r in z:
        byday[r["ts"].date().isoformat()] = byday.get(r["ts"].date().isoformat(), 0) + 1
    ks = sorted(byday)
    print("  days with zero-cost rows:", len(ks), "| last 8:", [(k, byday[k]) for k in ks[-8:]])
    print("  sample zero-cost row:", z[-1]["raw"][:170])
allday = {}
for r in rows:
    allday.setdefault(r["ts"].date().isoformat(), [0, 0])
    allday[r["ts"].date().isoformat()][0] += 1
    if r["cost"] == 0.0:
        allday[r["ts"].date().isoformat()][1] += 1
print("  last 8 days  (total_rows, zero_cost_rows):")
for k in sorted(allday)[-8:]:
    print("   ", k, allday[k])

print("\n=== Q3: is there a Codex-side wake log anywhere? ===")
pats = ["wake-agent*", "*codex*log*", "wake*codex*", "*codex*run*"]
base = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl")
print("  impl dir entries:")
for n in sorted(os.listdir(base)):
    p = os.path.join(base, n)
    kind = "dir " if os.path.isdir(p) else "file"
    size = "" if os.path.isdir(p) else " %d B" % os.path.getsize(p)
    print("   ", kind, n, size)
