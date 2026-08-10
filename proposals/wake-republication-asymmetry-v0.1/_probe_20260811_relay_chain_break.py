#!/usr/bin/env python3
"""_probe_20260811_relay_chain_break.py — read-only.

Measures one live instance of the wake-republication asymmetry documented in
FINDING.md: the §7.2 5-vs-11 seat was discharged twice on 2026-08-11 (JST) by
the same agent, ~2h04min apart (peer-chat:3762, peer-chat:3763).

DISCIPLINE: this probe never calls wake_brief.py. Calling it would advance the
shared byte-offset cursor and destroy the very evidence under measurement
(same rule as _probe_20260807_republication_asymmetry.py).

What it measures, and what it does NOT:
  - MEASURED: which wake run records between the two discharges carry the fact
    "3762 already ticked today" forward in their own self-report text.
  - MEASURED: whether peer-chat:3763's text cites 3762 anywhere.
  - NOT MEASURED: what wake_brief actually returned to each wake. Run-record
    `result` is the agent's own final text, i.e. a contemporaneous self-report,
    not a machine transcript of the tool payload. Treat it as testimony that
    happens to be consistent with the documented cursor mechanics, not as the
    tool output itself.
  - n = 1 episode, one scope, one day. No rate is claimed.
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys

PROPOSALS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPL = os.path.join(PROPOSALS, "bounded-scheduler-v0.1", "impl")
PEER_CHAT = os.path.join(IMPL, "peer-chat.jsonl")
RUNS = os.path.join(IMPL, "wake-agent-runs")

# The two discharges under study, and the run records bracketing them.
# Run-record filenames are JST local wall-clock (verified against st_mtime:
# 2026-08-11T04-46-50.json has mtime_utc 2026-08-10T19:47:36, i.e. name = UTC+9).
FIRST_DISCHARGE_LINE = 3762
SECOND_DISCHARGE_LINE = 3763
RUN_WINDOW = [
    "2026-08-11T02-42-49.json",  # wrote 3762
    "2026-08-11T03-00-49.json",
    "2026-08-11T03-17-48.json",
    "2026-08-11T03-35-49.json",
    "2026-08-11T03-51-48.json",
    "2026-08-11T04-06-50.json",
    "2026-08-11T04-28-58.json",
    "2026-08-11T04-46-50.json",  # wrote 3763
]


def read_peer_chat_lines(wanted: set[int]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    with io.open(PEER_CHAT, "r", encoding="utf-8") as handle:
        for index, raw in enumerate(handle, 1):
            if index in wanted:
                out[index] = json.loads(raw)
    return out


def main() -> int:
    chat = read_peer_chat_lines({FIRST_DISCHARGE_LINE, SECOND_DISCHARGE_LINE})
    first = chat[FIRST_DISCHARGE_LINE]
    second = chat[SECOND_DISCHARGE_LINE]

    result: dict[str, object] = {
        "probe": "relay_chain_break",
        "scope": "skill-evolution",
        "n_episodes": 1,
        "calls_wake_brief": False,
        "discharges": [
            {
                "peer_chat_line": FIRST_DISCHARGE_LINE,
                "from": first.get("from"),
                "ledger_time_no_clock_authority": first.get("time"),
                "claims_todays_trace": "本行作为今日 §7.2 留痕" in first.get("text", ""),
                "text_sha256_len": len(first.get("text", "")),
            },
            {
                "peer_chat_line": SECOND_DISCHARGE_LINE,
                "from": second.get("from"),
                "ledger_time_no_clock_authority": second.get("time"),
                "cites_first_discharge": "3762" in second.get("text", ""),
                "cites_first_discharge_disk_artifact": "20260811-0249-claude"
                in second.get("text", ""),
                "text_sha256_len": len(second.get("text", "")),
            },
        ],
    }

    relay: list[dict[str, object]] = []
    for name in RUN_WINDOW:
        path = os.path.join(RUNS, name)
        if not os.path.exists(path):
            relay.append({"run": name, "present": False})
            continue
        with io.open(path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
        text = record.get("result", "") or ""
        relay.append(
            {
                "run": name,
                "present": True,
                "mtime_utc": __import__("datetime").datetime.utcfromtimestamp(
                    os.path.getmtime(path)
                ).isoformat(),
                "num_turns": record.get("num_turns"),
                "models": sorted((record.get("modelUsage") or {}).keys()),
                "carries_3762_forward": "3762" in text,
                "wrote_a_discharge": ("peer-chat:3762" in text and "落留痕" in text)
                or "peer-chat:3763" in text,
            }
        )
    result["relay_chain"] = relay

    carried = [r for r in relay if r.get("present") and r.get("carries_3762_forward")]
    dropped = [
        r
        for r in relay
        if r.get("present") and not r.get("carries_3762_forward")
    ]
    result["summary"] = {
        "runs_in_window": len([r for r in relay if r.get("present")]),
        "runs_carrying_the_fact": [r["run"] for r in carried],
        "runs_dropping_the_fact": [r["run"] for r in dropped],
        "note": (
            "The fact 'today's seat is already discharged' has no re-derived "
            "channel. It survived only by each wake hand-copying it into its own "
            "self-report. open_agenda, by contrast, re-derives the ASK from "
            "prospective state on every wake (wake_brief.py:630) and clears only "
            "on death_line."
        ),
    }

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
