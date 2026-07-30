"""Append the double-signed implementation delegation to codex-inbox.jsonl."""
import secrets
import sys
from pathlib import Path

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
sys.path.insert(0, str(IMPL))
from append_clocked_jsonl import append_clocked_row  # noqa: E402

MSG = Path(__file__).with_name("_msg_20260730_delegate_impl.txt")
text = MSG.read_text(encoding="utf-8")

row = append_clocked_row(
    root=IMPL,
    ledger_name="codex-inbox.jsonl",
    payload={"id": secrets.token_hex(6), "from": "claude", "text": text},
)
print(row["id"], row["time"], len(text), "chars")
