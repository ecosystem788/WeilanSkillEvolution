"""Read-only: dump a line range of peer-chat in full."""
import io
import json
import sys

lo, hi = int(sys.argv[1]), int(sys.argv[2])
with io.open("peer-chat.jsonl", encoding="utf-8") as fh:
    for n, line in enumerate(fh, 1):
        line = line.strip()
        if not line or n < lo or n > hi:
            continue
        try:
            r = json.loads(line)
        except Exception:
            r = {"from": "?", "time": "?", "text": line}
        print("=" * 70)
        print("#%d %s from=%s re=%s" % (n, r.get("time"), r.get("from"),
                                        r.get("re")))
        print(r.get("text", ""))
