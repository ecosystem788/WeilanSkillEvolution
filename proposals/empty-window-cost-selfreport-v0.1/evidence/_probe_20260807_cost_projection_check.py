"""Read-only probe: falsification test of peer-chat:3564 cost projection.

Claims under test (all mine, from 3564):
  C1: today = 38 Claude model turns, $85.83
  C2: 11 of them were "honest-idle" turns, $13.08 total, mean $1.19
  C3: median cadence 22 min/turn
  C4: therefore empty window to 2026-08-10T00:00Z ~= 171 turns ~= $203
  C5: "$203 is Claude-side only; Codex-side cost in this log is always 0, not counted"

Nothing is written. No ledger call, no cursor advance.
"""
import io, os, re, json, statistics
from datetime import datetime, timedelta, timezone

ROOT = r"D:/WeilanSkillEvolution"
LOG = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl/wake-agent.log")
RUNS = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl/wake-agent-runs")

JST = timezone(timedelta(hours=9))
LINE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})\s+rc=(?P<rc>-?\d+)\s+(?P<status>\S+)"
    r"(?:\s+turns=(?P<turns>\d+))?(?:\s+cost=\$(?P<cost>[\d.]+))?(?P<rest>.*)$"
)

rows = []
unparsed = 0
for raw in io.open(LOG, encoding="utf-8", errors="replace").read().splitlines():
    if not raw.strip():
        continue
    m = LINE.match(raw.strip())
    if not m:
        unparsed += 1
        continue
    ts = datetime.strptime(m.group("ts"), "%Y-%m-%dT%H-%M-%S").replace(tzinfo=JST)
    rows.append({
        "ts": ts,
        "rc": int(m.group("rc")),
        "status": m.group("status"),
        "turns": int(m.group("turns")) if m.group("turns") else None,
        "cost": float(m.group("cost")) if m.group("cost") else None,
        "rest": m.group("rest").strip(),
        "raw": raw.strip(),
    })

print("log_lines_parsed", len(rows), "unparsed", unparsed)

# ---- what fields distinguish agents? ----
print("\n--- distinct 'rest' shapes (first 6) ---")
seen = {}
for r in rows:
    key = re.sub(r"wf-\S+", "wf-<id>", r["rest"])
    seen.setdefault(key, 0)
    seen[key] += 1
for k, v in sorted(seen.items(), key=lambda kv: -kv[1])[:6]:
    print(v, "|", k[:160])

# ---- is Codex in this same log? ----
print("\n--- does the log name an agent anywhere? ---")
hits = [r["raw"] for r in rows if "codex" in r["raw"].lower()]
print("lines mentioning codex:", len(hits))
for h in hits[:3]:
    print("  ", h[:180])

# ---- today's slice (JST day 2026-08-07) ----
day0 = datetime(2026, 8, 7, 0, 0, 0, tzinfo=JST)
day1 = day0 + timedelta(days=1)
today = [r for r in rows if day0 <= r["ts"] < day1]
costed = [r for r in today if r["cost"] is not None]
print("\n--- today (JST 2026-08-07) ---")
print("runs_logged", len(today), "runs_with_cost", len(costed),
      "runs_cost_zero", sum(1 for r in costed if r["cost"] == 0))
print("total_cost  $%.2f" % sum(r["cost"] for r in costed))

# split at 3564 (18:12:19 JST)
cut = datetime(2026, 8, 7, 18, 12, 19, tzinfo=JST)
before = [r for r in costed if r["ts"] < cut]
after = [r for r in costed if r["ts"] >= cut]
print("\nC1 test (state at 3564): runs_before=%d  cost_before=$%.2f   [3564 said 38 turns / $85.83]"
      % (len(before), sum(r["cost"] for r in before)))
print("since 3564:            runs_after =%d  cost_after =$%.2f" % (len(after), sum(r["cost"] for r in after)))
if after:
    print("  per-run cost since 3564: " + ", ".join("$%.2f" % r["cost"] for r in after))
    print("  mean $%.2f  median $%.2f" % (
        sum(r["cost"] for r in after) / len(after),
        statistics.median([r["cost"] for r in after])))

# ---- C3: cadence ----
def gaps(seq):
    return [ (seq[i]["ts"] - seq[i-1]["ts"]).total_seconds() / 60.0 for i in range(1, len(seq)) ]

g_today = gaps(today)
g_after = gaps([r for r in today if r["ts"] >= cut])
if g_today:
    print("\nC3 test: today cadence median %.1f min (n=%d gaps)  [3564 said 22 min]"
          % (statistics.median(g_today), len(g_today)))
if g_after:
    print("         since-3564 cadence median %.1f min (n=%d gaps)"
          % (statistics.median(g_after), len(g_after)))

# ---- C4: re-derive the projection with observed-since-3564 numbers ----
now = max(r["ts"] for r in rows)
window_end = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc).astimezone(JST)
hours_left = (window_end - now).total_seconds() / 3600.0
print("\nC4 re-derivation: last_logged_run=%s  window_end=%s  hours_left=%.1f"
      % (now.isoformat(), window_end.isoformat(), hours_left))
for label, cad, per in [
    ("3564 assumption", 22.0, 1.19),
    ("observed since 3564", statistics.median(g_after) if g_after else float("nan"),
     (sum(r["cost"] for r in after) / len(after)) if after else float("nan")),
]:
    if cad == cad and per == per:
        n = hours_left * 60.0 / cad
        print("  %-22s cadence %.1f min, $%.2f/run -> %.0f runs, $%.0f" % (label, cad, per, n, n * per))

# ---- C5: Codex side ----
print("\nC5 test: is there a separate Codex run record?")
if os.path.isdir(RUNS):
    names = sorted(os.listdir(RUNS))
    print("  wake-agent-runs entries:", len(names))
    todays = [n for n in names if "20260807" in n or "2026-08-07" in n]
    print("  today-ish entries:", len(todays))
    for n in todays[-6:]:
        print("   ", n)
    pat = {}
    for n in names:
        k = re.sub(r"[0-9]", "#", n)
        pat[k] = pat.get(k, 0) + 1
    print("  name patterns:", sorted(pat.items(), key=lambda kv: -kv[1])[:5])
else:
    print("  no wake-agent-runs dir")
