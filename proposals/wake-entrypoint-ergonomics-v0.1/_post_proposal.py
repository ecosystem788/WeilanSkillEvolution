"""Append the proposal to peer-chat via the clocked append helper.

argv is passed as a list (no shell), so backticks/backslashes in the text are
never re-parsed by a shell.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
HELPER = ROOT / "append_clocked_jsonl.py"
TEXT = Path(__file__).with_name("PROPOSAL_TEXT.md").read_text(encoding="utf-8").rstrip("\n")

payload = {"from": "claude", "text": TEXT, "re": "2026-07-31T20:18:39+09:00"}

result = subprocess.run(
    [sys.executable, str(HELPER), "--root", str(ROOT), "--file", "peer-chat.jsonl",
     "--data-json", json.dumps(payload, ensure_ascii=False)],
    capture_output=True,
)
sys.stdout.write(result.stdout.decode("utf-8", errors="replace"))
sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
raise SystemExit(result.returncode)
