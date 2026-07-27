import json, sys
from pathlib import Path

ROOT = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\wake-codex-runs")
OUT = Path(r"D:\WeilanSkillEvolution\proposals\codex-run-log-encoding-v0.1\census.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def decode(raw):
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16"), "utf-16le-bom"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-bom"
    return raw.decode("utf-8"), "utf-8"

rows = []
for i, p in enumerate(sorted(ROOT.glob("*.jsonl"))):
    raw = p.read_bytes()
    rec = {"name": p.name, "bytes": len(raw)}
    try:
        text, enc = decode(raw)
    except UnicodeDecodeError as exc:
        rec.update(enc="DECODE_FAIL", detail=str(exc)[:120])
        rows.append(rec); continue
    rec["enc"] = enc
    total = bad = 0
    auth = False
    auth_kinds = set()
    bad_lines = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        total += 1
        try:
            row = json.loads(line)
        except Exception as exc:
            bad += 1
            if len(bad_lines) < 4:
                bad_lines.append({"line": n, "err": str(exc)[:80], "head": line[:60]})
            continue
        if not isinstance(row, dict):
            continue
        t = row.get("type")
        if t == "turn.completed":
            auth = True; auth_kinds.add("turn.completed")
        elif t == "item.completed":
            it = row.get("item")
            if isinstance(it, dict) and isinstance(it.get("type"), str) and it["type"] != "error":
                auth = True; auth_kinds.add("item:" + it["type"])
    rec.update(lines=total, bad=bad, authentic=auth,
               auth_kinds=sorted(auth_kinds), bad_lines=bad_lines)
    rows.append(rec)
    if i % 200 == 0:
        print(i, p.name, flush=True)

OUT.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
print("WROTE", OUT, len(rows))
