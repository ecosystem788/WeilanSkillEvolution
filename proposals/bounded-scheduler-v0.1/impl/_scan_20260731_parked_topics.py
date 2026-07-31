"""Read-only scan: which parked-FINDING topics has Codex spoken to in peer-chat?"""
import io
import json
import sys

KW = sys.argv[1:] or ["见证", "witness", "longpath", "克隆",
                      "wake-agent-runs", "observability"]

rows = []
bad = 0
with io.open("peer-chat.jsonl", encoding="utf-8") as fh:
    for n, line in enumerate(fh, 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((n, json.loads(line)))
        except Exception:
            bad += 1
            rows.append((n, {"from": "?", "time": "?", "text": line}))

print("lines=%d unparsed=%d" % (len(rows), bad))
for n, r in rows:
    t = r.get("text", "")
    if any(k in t for k in KW):
        print("%5d %s %-6s %s" % (n, r.get("time"), r.get("from"),
                                  t[:120].replace("\n", " ")))
