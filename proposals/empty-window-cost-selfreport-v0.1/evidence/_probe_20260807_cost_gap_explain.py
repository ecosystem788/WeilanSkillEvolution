"""Read-only follow-up: explain the two gaps found by the first probe.

G1: probe says 39 runs / $106.73 before 3564; 3564 claimed 38 turns / $85.83.
G2: 3564 said "Codex-side cost in this log is always 0". Probe found 0 lines
    mentioning codex and 0 zero-cost rows today. Is Codex in this log at all?
"""
import io, os, re, json
from datetime import datetime, timedelta, timezone

ROOT = r"D:/WeilanSkillEvolution"
LOG = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl/wake-agent.log")
RUNS = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl/wake-agent-runs")
JST = timezone(timedelta(hours=9))
LINE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})\s+rc=(?P<rc>-?\d+)\s+(?P<status>\S+)"
    r"(?:\s+turns=(?P<turns>\d+))?(?:\s+cost=\$(?P<cost>[\d.]+))?(?P<rest>.*)$")

rows, unparsed = [], []
for raw in io.open(LOG, encoding="utf-8", errors="replace").read().splitlines():
    if not raw.strip():
        continue
    m = LINE.match(raw.strip())
    if not m:
        unparsed.append(raw.strip())
        continue
    ts = datetime.strptime(m.group("ts"), "%Y-%m-%dT%H-%M-%S").replace(tzinfo=JST)
    rows.append({"ts": ts, "status": m.group("status"),
                 "cost": float(m.group("cost")) if m.group("cost") else None,
                 "raw": raw.strip()})

print("=== unparsed lines (%d), first 8 ===" % len(unparsed))
for u in unparsed[:8]:
    print("  ", u[:170])

cut = datetime(2026, 8, 7, 18, 12, 19, tzinfo=JST)

print("\n=== G1: which day-window reproduces '38 turns / $85.83'? ===")
cands = {
    "JST day (00:00 JST)":  datetime(2026, 8, 7, 0, 0, tzinfo=JST),
    "UTC day (09:00 JST)":  datetime(2026, 8, 7, 9, 0, tzinfo=JST),
    "last 24h before 3564": cut - timedelta(hours=24),
    "last 12h before 3564": cut - timedelta(hours=12),
}
for label, start in cands.items():
    sel = [r for r in rows if start <= r["ts"] < cut and r["cost"] is not None]
    print("  %-22s n=%-3d cost=$%.2f" % (label, len(sel), sum(r["cost"] for r in sel)))
print("  3564 asserted        n=38  cost=$85.83")

print("\n=== G2: does any run record name its agent? ===")
names = sorted(n for n in os.listdir(RUNS) if n.endswith(".json"))
print("run json files:", len(names), " last:", names[-1])
sample = names[-1]
try:
    d = json.load(io.open(os.path.join(RUNS, sample), encoding="utf-8-sig"))
    if isinstance(d, dict):
        print("keys of %s:" % sample, sorted(d.keys())[:25])
        for k in ("agent", "who", "role", "model", "session_id", "cwd", "prompt_file", "subtype"):
            if k in d:
                print("   %s = %s" % (k, str(d[k])[:120]))
except Exception as e:
    txt = io.open(os.path.join(RUNS, sample), encoding="utf-8", errors="replace").read()
    print("not a single json object (%s); head:" % type(e).__name__, txt[:300])

print("\n=== G2b: do Codex chat posts line up with any log run start? ===")
codex_posts = ["18:20:32", "19:01:05", "20:13:00", "20:33:35", "20:56:44"]
claude_posts = ["18:12:19", "18:31:33", "20:01:57", "20:23:03", "20:41:45"]
day_runs = [r for r in rows if r["ts"] >= datetime(2026, 8, 7, 17, 0, tzinfo=JST)]
print("log runs since 17:00 JST:", ", ".join(r["ts"].strftime("%H:%M:%S") for r in day_runs))
def nearest_prior(hhmmss):
    t = datetime.strptime("2026-08-07T" + hhmmss, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=JST)
    prior = [r for r in day_runs if r["ts"] <= t]
    if not prior:
        return None
    r = max(prior, key=lambda x: x["ts"])
    return r["ts"].strftime("%H:%M:%S"), (t - r["ts"]).total_seconds() / 60.0
for label, posts in (("claude", claude_posts), ("codex", codex_posts)):
    print(" ", label)
    for p in posts:
        res = nearest_prior(p)
        print("    post %s -> nearest prior run %s  (+%.1f min)" % (p, res[0], res[1]) if res else "    post %s -> none" % p)

print("\n=== G2c: any zero-cost rows anywhere in the log? ===")
z = [r for r in rows if r["cost"] == 0.0]
print("zero-cost rows all-time:", len(z))
nocost = [r for r in rows if r["cost"] is None]
print("rows with literal '?' cost:", len(nocost), " (last:", nocost[-1]["ts"].isoformat() if nocost else "-", ")")
