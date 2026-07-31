"""Append this round's two peer-chat messages via the host-clock helper."""
import io
import sys
from pathlib import Path

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
sys.path.insert(0, str(IMPL))
from append_clocked_jsonl import append_clocked_row  # noqa: E402

HERE = Path(__file__).resolve().parent

rows = [
    ("_chat_20260731_to_codex.txt", {"from": "claude", "re": "2026-07-31T17:01:40+09:00"}),
    ("_chat_20260731_to_owner.txt", {"from": "claude"}),
]

for name, meta in rows:
    text = io.open(HERE / name, encoding="utf-8").read().rstrip("\n")
    payload = dict(meta)
    payload["text"] = text
    row = append_clocked_row(root=IMPL, ledger_name="peer-chat.jsonl", payload=payload)
    print(row["time"], len(text), "chars ->", name)
