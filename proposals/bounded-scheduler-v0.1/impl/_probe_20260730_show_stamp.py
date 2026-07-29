import io, json, sys

LEDGER = ("D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/"
          "peer-chat.jsonl")
stamps = set(sys.argv[1:-1])
needle = sys.argv[-1]
for n, raw in enumerate(io.open(LEDGER, encoding="utf-8"), 1):
    try:
        o = json.loads(raw)
    except Exception:
        continue
    if o.get("time") in stamps:
        print("=== line", n, o.get("from"), o.get("time"))
        for ln in (o.get("text") or "").split("\n"):
            if needle in ln:
                print("   ", ln.strip()[:400])
