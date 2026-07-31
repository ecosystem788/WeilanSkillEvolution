#!/usr/bin/env python3
"""Read-only probe: for handoff goals that closed, did the goal's clock cause the closure?

Each handoff goal registers a clock condition with a `not_before_utc`. The goal's purpose
is that when that clock fires, a waking member sees the item and adjudicates it. This
probe tests whether that is what actually happened, by comparing, per closed goal:

  * not_before_utc        -- when the reminder was scheduled to become eligible
  * adjudication_time     -- the peer-chat message cited in the transition reason
  * causal_event_observed -- whether any causal event was ever recorded for the condition

If adjudication_time < not_before_utc, the conversation resolved the item before the
reminder was even eligible, so the goal cannot have caused the closure.

The transition reasons cite their evidence as `peer-chat.jsonl:<line>`; this probe parses
that reference and reads the *actual* timestamp from the chat ledger rather than trusting
the prose, so a mis-stated reason shows up as a mismatch instead of being inherited.

Usage:  python _probe_20260801_goal_vs_conversation.py [--json OUT]
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime

WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
CHAT = os.path.join(
    WORKSPACE, "proposals", "bounded-scheduler-v0.1", "impl", "peer-chat.jsonl"
)

HANDOFF_MARKERS = [
    "留给你独立判", "留给 Codex 独立判", "留给Codex独立判", "刻意不选", "刻意没选",
]
CITE_RE = re.compile(r"peer-chat\.jsonl[:：](\d+)")


def parse_time(s):
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # legacy rows use "YYYY-MM-DD HH:MM:SS" with no offset; treat as naive/unknown
        try:
            dt = datetime.fromisoformat(s.replace(" ", "T"))
        except ValueError:
            return None
    return dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="out")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(here, "_prospective_snapshot.tmp.json")
    with open(tmp, "wb") as fh:
        subprocess.run(
            [sys.executable, TRACE, "prospective-show",
             "--workspace", WORKSPACE, "--scope", SCOPE],
            stdout=fh, stderr=subprocess.DEVNULL, check=True,
        )
    with io.open(tmp, encoding="utf-8-sig") as fh:
        snap = json.load(fh)
    goals = snap["goals"]

    chat = {}
    with io.open(CHAT, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chat[i] = json.loads(line)
            except ValueError:
                pass

    rows = []
    for ref, g in goals.items():
        desc = g.get("description") or ""
        if not any(m in desc for m in HANDOFF_MARKERS):
            continue
        if g.get("state") == "ACTIVE":
            continue
        reason = g.get("transition_reason") or ""
        cond = g.get("condition") or {}
        nb = cond.get("not_before_utc")
        nb_dt = parse_time(nb)

        cited = []
        for m in CITE_RE.finditer(reason):
            n = int(m.group(1))
            row = chat.get(n)
            cited.append({
                "line": n,
                "resolved": row is not None,
                "time": (row or {}).get("time"),
                "from": (row or {}).get("from"),
                # ledger `time` carries no clock authority unless written by the host
                # clock helper; without this the day-scale comparison below could be
                # an artifact of hand-written timestamps.
                "time_authority": (row or {}).get("time_authority"),
            })
        # earliest cited peer message = when the adjudication actually appeared
        times = [parse_time(c["time"]) for c in cited if c.get("time")]
        times = [t for t in times if t is not None and t.tzinfo is not None]
        adj_dt = min(times) if times else None

        verdict = "unknown"
        lead_hours = None
        if adj_dt is not None and nb_dt is not None and nb_dt.tzinfo is not None:
            # positive = adjudication landed this many hours BEFORE the clock was eligible
            lead_hours = round((nb_dt - adj_dt).total_seconds() / 3600.0, 2)
            verdict = "adjudicated_before_clock_eligible" if adj_dt < nb_dt \
                else "adjudicated_after_clock_eligible"

        rows.append({
            "goal_ref": ref,
            "state": g.get("state"),
            "registered_sequence": g.get("registered_sequence"),
            "not_before_utc": nb,
            "cited_chat_rows": cited,
            "adjudication_time": adj_dt.isoformat() if adj_dt else None,
            "causal_event_id": g.get("causal_event_id"),
            "causal_event_observed": bool(g.get("causal_event_id")),
            "lead_hours_before_clock": lead_hours,
            "verdict": verdict,
        })

    rows.sort(key=lambda r: r["registered_sequence"] or 0)
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    leads = sorted(
        r["lead_hours_before_clock"] for r in rows
        if r["verdict"] == "adjudicated_before_clock_eligible"
    )
    median_lead = leads[len(leads) // 2] if leads else None

    result = {
        "probe": "goal-vs-conversation",
        "read_only": True,
        "closed_handoff_goals": len(rows),
        "verdict_counts": counts,
        "lead_hours_before_clock_sorted": leads,
        "median_lead_hours_before_clock": median_lead,
        "with_causal_event": sum(1 for r in rows if r["causal_event_observed"]),
        "unresolved_citations": sum(
            1 for r in rows for c in r["cited_chat_rows"] if not c["resolved"]
        ),
        "cited_rows_total": sum(len(r["cited_chat_rows"]) for r in rows),
        "cited_rows_with_clock_authority": sum(
            1 for r in rows for c in r["cited_chat_rows"]
            if c.get("time_authority") == "clock"
        ),
        "goals": rows,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
