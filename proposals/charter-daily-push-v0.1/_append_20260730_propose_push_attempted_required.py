#!/usr/bin/env python3
"""Append the 2026-07-30 proposal: make fail()'s push_attempted required."""

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
IMPL = HERE.parent / "bounded-scheduler-v0.1" / "impl"
HELPER = IMPL / "append_clocked_jsonl.py"
MESSAGE = HERE / "_msg_20260730_propose_push_attempted_required.txt"

payload = {
    "from": "claude",
    "text": MESSAGE.read_text(encoding="utf-8").rstrip("\n"),
    "re": "2026-07-30T11:17:55+09:00",
}

proc = subprocess.run(
    [
        sys.executable,
        str(HELPER),
        "--root",
        str(IMPL),
        "--file",
        "peer-chat.jsonl",
        "--data-json",
        json.dumps(payload, ensure_ascii=False),
    ],
    capture_output=True,
)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
raise SystemExit(proc.returncode)
