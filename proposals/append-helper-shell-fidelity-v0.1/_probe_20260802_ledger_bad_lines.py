"""Read-only: locate strictly-unparseable lines in peer-chat.jsonl and friends."""
import io, json, os, hashlib

ROOT = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"
FILES = ["peer-chat.jsonl", "owner-inbox.jsonl", "owner-inbox-replies.jsonl",
         "owner-inbox-processed.jsonl", "codex-inbox.jsonl",
         "codex-inbox-replies.jsonl", "codex-inbox-processed.jsonl"]

out = {}
for name in FILES:
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        out[name] = {"exists": False}
        continue
    bad = []
    total = 0
    with io.open(p, "rb") as fh:
        raw_lines = fh.read().split(b"\n")
    for i, rb in enumerate(raw_lines, start=1):
        s = rb.decode("utf-8", errors="replace").strip()
        if not s:
            continue
        total += 1
        try:
            json.loads(s)
        except Exception as e:
            rec = {
                "line": i,
                "error": str(e),
                "sha256_raw": hashlib.sha256(rb).hexdigest(),
                "len": len(rb),
                "head": s[:160],
            }
            # locate the offending column
            col = getattr(e, "colno", None)
            if col:
                rec["around"] = s[max(0, col - 60):col + 60]
            bad.append(rec)
    out[name] = {"exists": True, "total_nonblank": total, "bad_count": len(bad), "bad": bad}

print(json.dumps(out, ensure_ascii=False, indent=2))
