import json, sys
p = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl"
start = int(sys.argv[1]); end = int(sys.argv[2])
full = len(sys.argv) > 3 and sys.argv[3] == "full"
with open(p, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if not (start <= i <= end):
            continue
        try:
            d = json.loads(line)
        except Exception as e:
            print(i, "PARSE_ERR", e); continue
        t = d.get("text", "")
        if not full:
            t = t[:400]
        print("=" * 8, i, d.get("from"), d.get("time"), "re=", d.get("re"))
        print(t)
