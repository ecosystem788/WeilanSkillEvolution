#!/usr/bin/env python3
"""Read-only probe: the base rate. Of every handoff goal EVER registered, how many closed?

The companion probe only inspected ACTIVE goals, where "never transitioned" is true by
definition. This one scans the whole prospective ledger so the denominator includes
handoff goals that did reach a terminal state. Without it, "0 of 11" is a tautology.

Usage:  python _probe_20260801_handoff_base_rate.py [--json OUT]
"""
import argparse
import io
import json
import os
import subprocess
import sys

WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"

HANDOFF_MARKERS = [
    "留给你独立判", "留给 Codex 独立判", "留给Codex独立判", "刻意不选", "刻意没选",
]


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
        goals = json.load(fh)["goals"]

    handoff, states = [], {}
    for ref, g in goals.items():
        desc = g.get("description") or ""
        if not any(m in desc for m in HANDOFF_MARKERS):
            continue
        st = g.get("state")
        states[st] = states.get(st, 0) + 1
        handoff.append({
            "goal_ref": ref,
            "state": st,
            "registered_sequence": g.get("registered_sequence"),
            "transition_reason": (g.get("transition_reason") or "")[:400],
            "causal_event_id": g.get("causal_event_id"),
        })
    handoff.sort(key=lambda h: h["registered_sequence"] or 0)

    all_states = {}
    for g in goals.values():
        all_states[g.get("state")] = all_states.get(g.get("state"), 0) + 1

    result = {
        "probe": "handoff-base-rate",
        "read_only": True,
        "goals_total": len(goals),
        "goals_by_state": all_states,
        "handoff_goals_total": len(handoff),
        "handoff_goals_by_state": states,
        "handoff_goals": handoff,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
