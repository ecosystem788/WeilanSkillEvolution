#!/usr/bin/env python3
"""Append the 1bc5727 review to peer-chat with a host-clock timestamp."""

import pathlib
import sys

IMPL = pathlib.Path(
    "D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl"
)
sys.path.insert(0, str(IMPL))

from append_clocked_jsonl import append_clocked_row  # noqa: E402

TEXT = (
    pathlib.Path(__file__)
    .with_name("_msg_20260730_review_push_attempted_required.txt")
    .read_text(encoding="utf-8")
    .rstrip("\n")
)

row = append_clocked_row(
    root=IMPL,
    ledger_name="peer-chat.jsonl",
    payload={
        "from": "claude",
        "re": "2026-07-30T12:05:38+09:00",
        "text": TEXT,
    },
)
print(row["time"], len(TEXT))
