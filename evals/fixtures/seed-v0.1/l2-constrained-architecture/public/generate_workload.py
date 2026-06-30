import json
from pathlib import Path


def main():
    target = Path(__file__).parent / "workload" / "events.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(10000):
        event = {"event_id": f"evt-{index:05d}", "kind": ["created", "updated", "closed"][index % 3], "sequence": index, "payload": (f"p{index:05d}-" * 31)[:240]}
        rows.append(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    target.write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
