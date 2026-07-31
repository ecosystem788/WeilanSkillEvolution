#!/usr/bin/env python3
"""Read-only probe: did the "candidates left for you to judge" handoffs ever get judged?

Method (all read-only, no writes to any ledger):
  1. From the prospective ledger, take every goal whose state is ACTIVE.
  2. Keep the ones whose description contains an explicit handoff phrase
     (a variant of "the candidates I deliberately did not pick, left for you to judge").
  3. For each, extract the proposal directory slug it points at (proposals/<slug>/).
  4. Scan peer-chat.jsonl for messages from the *other* member (codex) that name that
     slug, dated at or after the goal's registration.
  5. Report per goal: handoff present, slug, count of peer messages naming the slug,
     and the timestamps of those messages.

Nothing here decides whether such a message *is* an adjudication -- naming the slug is a
necessary condition only. A zero count is therefore a sound negative (the peer never
mentioned it); a non-zero count is a candidate that a human/agent must read.

Usage:  python _probe_20260801_handoff_completion.py [--json OUT]
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
CHAT = os.path.join(
    WORKSPACE, "proposals", "bounded-scheduler-v0.1", "impl", "peer-chat.jsonl"
)

# Explicit handoff phrasing used across these findings. Kept as substrings so that
# punctuation-width variants (full-width vs half-width quotes) all match.
HANDOFF_MARKERS = [
    "留给你独立判",
    "留给 Codex 独立判",
    "留给Codex独立判",
    "刻意不选",
    "刻意没选",
]

SLUG_RE = re.compile(r"proposals[/\\]([A-Za-z0-9][A-Za-z0-9._-]*)[/\\]")


def load_goals(tmp_path):
    """Run prospective-show and return its goals dict."""
    with open(tmp_path, "wb") as fh:
        subprocess.run(
            [
                sys.executable, TRACE, "prospective-show",
                "--workspace", WORKSPACE, "--scope", SCOPE,
            ],
            stdout=fh, stderr=subprocess.DEVNULL, check=True,
        )
    with io.open(tmp_path, encoding="utf-8-sig") as fh:
        return json.load(fh)["goals"]


def load_chat():
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
    return rows


def goal_slug(desc):
    """The proposal dir a goal points at: the most frequent slug in its description."""
    hits = SLUG_RE.findall(desc or "")
    if not hits:
        return None
    counts = {}
    for h in hits:
        counts[h] = counts.get(h, 0) + 1
    # ties broken by first appearance, so the anchor slug wins over incidental refs
    best = max(counts.items(), key=lambda kv: (kv[1], -hits.index(kv[0])))
    return best[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="out")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    goals = load_goals(os.path.join(here, "_prospective_snapshot.tmp.json"))
    chat = load_chat()

    codex_rows = [(n, r) for n, r in chat if r.get("from") == "codex"]

    findings = []
    for ref, g in goals.items():
        if g.get("state") != "ACTIVE":
            continue
        desc = g.get("description") or ""
        marker = next((m for m in HANDOFF_MARKERS if m in desc), None)
        if not marker:
            continue
        slug = goal_slug(desc)
        mentions = []
        if slug:
            for n, r in codex_rows:
                if slug in (r.get("text") or ""):
                    mentions.append({
                        "line": n,
                        "time": r.get("time"),
                        "excerpt": (r.get("text") or "")[:100],
                    })
        # Second, far narrower discriminator: does ANY chat message, from any author,
        # name this goal by its ref? A goal_ref is a unique string, so a hit here is an
        # explicit reference to the handoff itself rather than to its subject area.
        ref_hits = [
            {"line": n, "time": r.get("time"), "from": r.get("from")}
            for n, r in chat if ref in (r.get("text") or "")
        ]
        findings.append({
            "goal_ref": ref,
            "handoff_marker": marker,
            "registered_sequence": g.get("registered_sequence"),
            "death_line": g.get("death_line"),
            "slug": slug,
            "peer_mentions_of_slug": len(mentions),
            "chat_mentions_of_goal_ref": len(ref_hits),
            "goal_ref_hits": ref_hits,
            "transitioned": g.get("state") != "ACTIVE",
            "transition_reason": g.get("transition_reason"),
            "mentions": mentions,
        })

    findings.sort(key=lambda f: f["registered_sequence"] or 0)
    judged = [f for f in findings if f["peer_mentions_of_slug"] > 0]

    result = {
        "probe": "adjudication-handoff-completion",
        "read_only": True,
        "chat_line_count": len(chat),
        "chat_sha256": hashlib.sha256(
            io.open(CHAT, "rb").read()
        ).hexdigest(),
        "active_goals_total": sum(1 for g in goals.values() if g.get("state") == "ACTIVE"),
        "handoff_goals_total": len(findings),
        "handoff_goals_with_any_peer_mention": len(judged),
        "handoff_goals_with_zero_peer_mention": len(findings) - len(judged),
        "handoff_goals_named_by_ref_in_chat": sum(
            1 for f in findings if f["chat_mentions_of_goal_ref"] > 0
        ),
        "handoff_goals_transitioned": sum(1 for f in findings if f["transitioned"]),
        "goals": findings,
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
