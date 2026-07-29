import json, io, sys

path = r'D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl'
rows = []
with io.open(path, encoding='utf-8') as fh:
    for i, line in enumerate(fh, 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((i, json.loads(line)))
        except Exception as exc:
            rows.append((i, {"from": "?PARSE_ERROR", "time": "", "text": str(exc)}))

n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
for i, r in rows[-n:]:
    print('=== line', i, '|', r.get('from'), r.get('time'), '| re=', r.get('re'))
    print(r.get('text', '')[:2500])
    print()
