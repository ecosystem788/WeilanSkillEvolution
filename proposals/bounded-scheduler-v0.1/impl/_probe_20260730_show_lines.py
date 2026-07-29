import io, json, re, sys

LEDGER = ("D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/"
          "peer-chat.jsonl")
want = {int(a) for a in sys.argv[1:-1]}
needle = sys.argv[-1]
for n, raw in enumerate(io.open(LEDGER, encoding="utf-8"), 1):
    if n not in want:
        continue
    o = json.loads(raw)
    print("=== line", n, o.get("from"), o.get("time"))
    for ln in (o.get("text") or "").split("\n"):
        if needle in ln:
            print("   ", ln.strip())
