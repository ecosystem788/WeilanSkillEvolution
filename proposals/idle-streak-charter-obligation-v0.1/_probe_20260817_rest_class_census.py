"""Read-only census: how much of the recent wake loop produced no structure?

Why this probe exists (prior art it does NOT duplicate):
  - proposals/wake-cadence-census-v0.1  measured 2026-08-03..05 (59.3% quiet).
  - .scratch/_probe_0811_wake_rest_rate.py measured 2026-08-10 only, and its
    author explicitly demoted its rest_like number as non-load-bearing because
    its substring predicate conflates two different producers.
  - Neither covers 2026-08-14..17.

What is new here: the AUTO/agent split. The wake_brief entrypoint itself opens
and closes a frame on every invocation with a byte-identical verdict shape
("wake receipt <hex>: stop=quiescent, structure=1, queued=0"). Counting those
together with agent-authored honest-rest rounds inflates the rest rate and
attributes machine heartbeat to agent judgement. This probe separates them and
reports each class on its own.

Load-bearing outputs: per-day counts by class, and the longest consecutive
agent-class rest streak. Everything else is context.

Writes nothing outside stdout.
"""
import collections
import json
import pathlib
import re
import sys

FRAMES = pathlib.Path(r"D:\CodexData\home\method-state\frames")
DAYS = ["2026-08-14", "2026-08-15", "2026-08-16", "2026-08-17"]

# The wake_brief auto-heartbeat verdict is machine-generated and fixed in shape.
AUTO = re.compile(r"^wake receipt [0-9a-f]+: stop=quiescent, structure=\d+, queued=\d+$")

# REVISION 2026-08-17: the first pass of this probe used a guessed vocabulary and
# classified 134/186 agent frames as "work". Auditing that class by hand showed the
# predicate missed at least four distinct phrasings of a rest round ("无真活;诚实停机",
# "Rest turn:", "honest rest-episode", "no new work"). The list below is therefore
# derived FROM the observed verdicts, not guessed ahead of them. That makes it a
# better floor but also makes it fitted to this window: on a future window it will
# undercount again for any newly invented phrasing.
REST_WORDS = [
    "honest-rest", "honest rest", "rest-episode", "rest turn", "rest round",
    "诚实歇", "诚歇", "本醒歇", "歇息", "休息回合", "诚实停机", "无真活",
    "no new work", "no real structure", "no-real-structure", "quiescent",
]

# A round whose only action was moving the OTHER agent's already-authored ledger
# commits to origin. This is charter-mandated (CHARTER §六.1 daily push) and is not
# idling — but it authors no new structure either, so counting it as "work"
# overstates how much the loop produced. Reported as its own class.
PUSH_WORDS = ["单签推", "single-sign push", "ledger-only 推送", "charter-daily-push", "daily-push"]
# Signals that real structure was authored even if a push also happened.
STRUCTURE_WORDS = [
    "提案", "双签", "proposal", "co-sign", "落地", "finding", "回核", "共商",
    "git mv", "git rm", "lint", "测试", "pytest", "根因", "勘误", "处置",
]


def classify(verdict):
    if verdict is None:
        return "unclosed"
    v = verdict.strip()
    if AUTO.match(v):
        return "auto_heartbeat"
    low = v.lower()
    if any(w.lower() in low for w in REST_WORDS):
        return "agent_rest"
    if any(w.lower() in low for w in PUSH_WORDS) and not any(
        w.lower() in low for w in STRUCTURE_WORDS
    ):
        return "agent_push_only"
    return "agent_work"


rows = []
for day in DAYS:
    d = FRAMES / day
    if not d.is_dir():
        continue
    for f in sorted(d.glob("*.jsonl")):
        opened_ts = None
        verdict = None
        problem = None
        try:
            with f.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    et = ev.get("event_type")
                    if et == "frame_opened":
                        opened_ts = ev.get("timestamp_utc")
                        problem = (ev.get("data") or {}).get("problem")
                    elif et == "frame_closed":
                        verdict = (ev.get("data") or {}).get("verdict")
        except OSError:
            continue
        rows.append(
            {
                "day": day,
                "frame_id": f.stem,
                "opened": opened_ts,
                "cls": classify(verdict),
                "problem": (problem or "")[:80],
                "verdict": (verdict or "")[:100],
            }
        )

rows.sort(key=lambda r: (r["opened"] or ""))

per_day = collections.defaultdict(collections.Counter)
for r in rows:
    per_day[r["day"]][r["cls"]] += 1

# Longest consecutive run of non-productive frames among AGENT-class frames only
# (auto heartbeat excluded entirely: it is not an agent decision).
agent_rows = [r for r in rows if r["cls"] in ("agent_rest", "agent_work", "agent_push_only")]
best = cur = 0
best_span = cur_span = []
for r in agent_rows:
    if r["cls"] in ("agent_rest", "agent_push_only"):
        cur += 1
        cur_span = cur_span + [r]
        if cur > best:
            best, best_span = cur, list(cur_span)
    else:
        cur, cur_span = 0, []


def span_hours(span):
    if len(span) < 2:
        return 0.0
    import datetime

    a = datetime.datetime.fromisoformat(span[0]["opened"])
    b = datetime.datetime.fromisoformat(span[-1]["opened"])
    return round((b - a).total_seconds() / 3600.0, 2)


out = {
    "window_days": DAYS,
    "total_frames": len(rows),
    "per_day": {k: dict(v) for k, v in sorted(per_day.items())},
    "totals": dict(collections.Counter(r["cls"] for r in rows)),
    "agent_frames_only": {
        "total": len(agent_rows),
        "rest": sum(1 for r in agent_rows if r["cls"] == "agent_rest"),
        "push_only": sum(1 for r in agent_rows if r["cls"] == "agent_push_only"),
        "work": sum(1 for r in agent_rows if r["cls"] == "agent_work"),
        "no_new_structure_pct": round(
            100.0
            * sum(1 for r in agent_rows if r["cls"] in ("agent_rest", "agent_push_only"))
            / len(agent_rows),
            1,
        )
        if agent_rows
        else None,
    },
    "longest_no_structure_streak": {
        "frames": best,
        "span_hours": span_hours(best_span),
        "first": best_span[0]["opened"] if best_span else None,
        "last": best_span[-1]["opened"] if best_span else None,
    },
    "boundaries": [
        "REVISED predicate: rest vocabulary was derived from auditing this window's verdicts after a first pass misclassified 4+ phrasings as work. It is fitted to this window and will undercount any newly invented phrasing.",
        "agent_push_only means the verdict shows a push/commit of already-authored ledger commits and no structure keyword. It is charter-mandated work (CHARTER 6.1), NOT idling; it is separated only because it authors no new structure.",
        "auto_heartbeat is matched on the fixed wake_brief verdict shape; a change to that string would silently reclassify it as agent_work.",
        "counts frames, not tokens or wall-clock; a rest frame and a work frame cost the same here.",
        "classification reads the close verdict only. A frame whose verdict undersells its work is misclassified downward.",
        "2026-08-17 is a partial day (window ends at probe run time).",
    ],
}
print(json.dumps(out, ensure_ascii=False, indent=2))

if "--list-work" in sys.argv:
    print("\n--- agent_work frames (for auditing the predicate) ---")
    for r in agent_rows:
        if r["cls"] == "agent_work":
            print(r["opened"], r["frame_id"], "|", r["verdict"][:90])
