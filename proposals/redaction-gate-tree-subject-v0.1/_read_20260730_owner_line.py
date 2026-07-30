import io
import json

PATH = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl"

for number, line in enumerate(io.open(PATH, encoding="utf-8"), 1):
    line = line.strip()
    if not line:
        continue
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        continue
    if record.get("from") == "owner" and str(record.get("time", "")).startswith("2026-07-30"):
        print("=== line", number, "|", record.get("time"), "===")
        print(record.get("text"))
        print()
