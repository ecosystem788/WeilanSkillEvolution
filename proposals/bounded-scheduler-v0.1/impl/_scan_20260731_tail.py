"""Read-only: dump peer-chat tail messages in full."""
import io
import json
import sys

start = int(sys.argv[1]) if len(sys.argv) > 1 else -20
rows = []
with io.open("peer-chat.jsonl", encoding="utf-8") as fh:
    for n, line in enumerate(fh, 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((n, json.loads(line)))
        except Exception:
            rows.append((n, {"from": "?", "time": "?", "text": line}))

for n, r in rows[start:]:
    print("=" * 70)
    print("#%d %s  from=%s  re=%s" % (n, r.get("time"), r.get("from"),
                                      r.get("re")))
    print(r.get("text", ""))
