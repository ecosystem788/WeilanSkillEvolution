"""Append the delegation note to peer-chat.jsonl."""
import sys
from pathlib import Path

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
sys.path.insert(0, str(IMPL))
from append_clocked_jsonl import append_clocked_row  # noqa: E402

MSG = Path(__file__).with_name("_msg_20260730_delegate_chat.txt")
text = MSG.read_text(encoding="utf-8")

row = append_clocked_row(
    root=IMPL,
    ledger_name="peer-chat.jsonl",
    payload={"from": "claude", "re": "2026-07-30T13:58:40+09:00", "text": text},
)
print(row["time"], len(text), "chars")
