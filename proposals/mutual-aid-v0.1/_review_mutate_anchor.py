"""Review-only mutation harness: revert anchor selection to max(timestamp).

Copies the current module + tests into a temp dir, mutates ONLY the anchor
selection back to the pre-dual-sign behaviour, and leaves the dir for pytest.
Writes nothing into the repo except this file. authority: none.
"""
import io
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
DST = Path(sys.argv[1])

if DST.exists():
    shutil.rmtree(DST)
DST.mkdir(parents=True)
for name in ("peer_health_wake.py", "test_peer_health_wake.py"):
    shutil.copy2(SRC / name, DST / name)

target = DST / "peer_health_wake.py"
text = io.open(target, encoding="utf-8").read()

FWD_NEW = '''            source_head: tuple[int, dict] | None = None
            for line_number, row in _rows(path, parse_errors=parse_errors, **row_options):
                if row.get("from") == "codex":
                    source_head = (line_number, row)
            if source_head is not None:
                line_number, row = source_head
                stamp = _local_time_as_utc(row.get("time"))
                activities.append((stamp, f"{name}:{line_number}@{row['time']} (codex activity)"))'''

FWD_OLD = '''            for line_number, row in _rows(path, parse_errors=parse_errors, **row_options):
                if row.get("from") != "codex":
                    continue
                stamp = _local_time_as_utc(row.get("time"))
                activities.append((stamp, f"{name}:{line_number}@{row['time']} (codex activity)"))'''

REV_NEW = '''        if row.get("from") == "claude":
            peer_chat_head = (line_number, row)
    if peer_chat_head is not None:
        line_number, row = peer_chat_head
        stamp = _local_time_as_utc(row.get("time"))
        activities.append((stamp, f"peer-chat.jsonl:{line_number}@{row['time']} (claude activity)"))'''

REV_OLD = '''        if row.get("from") == "claude":
            stamp = _local_time_as_utc(row.get("time"))
            activities.append((stamp, f"peer-chat.jsonl:{line_number}@{row['time']} (claude activity)"))'''

REC_NEW = '''    receipt_head: tuple[int, dict] | None = None
    for line_number, row in _rows(root / "concurrent-receipts.jsonl", parse_errors=parse_errors):
        if str(row.get("wake_id", "")).startswith("claude-"):
            receipt_head = (line_number, row)
    if receipt_head is not None:
        line_number, row = receipt_head
        stamp = _local_time_as_utc(row.get("time"))
        activities.append((stamp, f"concurrent-receipts.jsonl:{line_number}@{row['time']} (claude wake)"))'''

REC_OLD = '''    for line_number, row in _rows(root / "concurrent-receipts.jsonl", parse_errors=parse_errors):
        if str(row.get("wake_id", "")).startswith("claude-"):
            stamp = _local_time_as_utc(row.get("time"))
            activities.append((stamp, f"concurrent-receipts.jsonl:{line_number}@{row['time']} (claude wake)"))'''

for label, new, old in (
    ("forward", FWD_NEW, FWD_OLD),
    ("reverse-chat", REV_NEW, REV_OLD),
    ("reverse-receipts", REC_NEW, REC_OLD),
):
    if new not in text:
        raise SystemExit(f"anchor block not found: {label}")
    text = text.replace(new, old)

io.open(target, "w", encoding="utf-8").write(text)
print(f"mutated {target}: anchor selection reverted to max(timestamp)")
