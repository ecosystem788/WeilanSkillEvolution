#!/usr/bin/env python3
"""Read-only probe: on turns that self-declared an empty higher-priority queue, what got chosen?

A wake whose author writes some variant of "no owner mail, no due goal, no unreviewed
peer receipt" has declared, in its own words, that `open_agenda` was the highest-priority
thing available to it. This probe counts those turns and classifies what the same message
went on to do:

  - "new_finding"  : the message announces a FINDING / new measurement (a new agenda item)
  - "agenda_pick"  : the message names an existing ACTIVE handoff goal_ref as the work done
  - "other"        : neither

It does not judge whether picking the agenda would have been better. It only measures
which of the two the idle turns actually produced.

Usage:  python _probe_20260801_idle_turn_choice.py [--json OUT]
"""
import argparse
import hashlib
import io
import json
import os
import sys

WORKSPACE = r"D:\WeilanSkillEvolution"
CHAT = os.path.join(
    WORKSPACE, "proposals", "bounded-scheduler-v0.1", "impl", "peer-chat.jsonl"
)

# Self-declarations that the higher-priority queues were empty this wake. Each is a
# phrase an author only writes when reporting its own wake state.
IDLE_MARKERS = [
    "没有话筒新话",
    "没有到期目标",
    "没有你未评审的回执",
    "没有观察员新话",
    "话筒没有新话",
    "收件箱没有新活",
    "没有新活",
]
# A message counts as idle-declaring only if it hits at least this many distinct markers,
# so that a passing mention of one phrase does not qualify.
IDLE_MIN_MARKERS = 2

FINDING_MARKERS = ["【FINDING", "FINDING·不开案", "我去量了", "我去量的"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="out")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    with io.open(
        os.path.join(here, "_probe_20260801_handoff_completion.out.json"),
        encoding="utf-8",
    ) as fh:
        handoff = json.load(fh)
    active_refs = [g["goal_ref"] for g in handoff["goals"]]

    rows = []
    with io.open(CHAT, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((i, json.loads(line)))
            except ValueError:
                continue

    idle = []
    for n, r in rows:
        text = r.get("text") or ""
        hit = [m for m in IDLE_MARKERS if m in text]
        if len(hit) < IDLE_MIN_MARKERS:
            continue
        named = [ref for ref in active_refs if ref in text]
        is_finding = any(m in text for m in FINDING_MARKERS)
        if named:
            kind = "agenda_pick"
        elif is_finding:
            kind = "new_finding"
        else:
            kind = "other"
        idle.append({
            "line": n,
            "time": r.get("time"),
            "from": r.get("from"),
            "markers_hit": hit,
            "classification": kind,
            "named_active_goal_refs": named,
            "excerpt": text[:140],
        })

    counts = {}
    for e in idle:
        counts[e["classification"]] = counts.get(e["classification"], 0) + 1

    result = {
        "probe": "idle-turn-choice",
        "read_only": True,
        "chat_line_count": len(rows),
        "chat_sha256": hashlib.sha256(io.open(CHAT, "rb").read()).hexdigest(),
        "idle_min_markers": IDLE_MIN_MARKERS,
        "idle_declaring_messages": len(idle),
        "classification_counts": counts,
        "messages": idle,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
