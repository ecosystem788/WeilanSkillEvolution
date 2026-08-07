import io, os, json, re
from datetime import datetime, timedelta, timezone

ROOT = r"D:/WeilanSkillEvolution"
CR = os.path.join(ROOT, "proposals/bounded-scheduler-v0.1/impl/wake-codex-runs")

def read_text(p):
    raw = open(p, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig")
    # heuristic: lots of NULs -> utf-16le without BOM
    if raw[:200].count(b"\x00") > 40:
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")

today = sorted(n for n in os.listdir(CR) if n.startswith("2026-08-07") and n.endswith(".jsonl"))
print("codex runs today (.jsonl):", len(today))

tot_in = tot_cached = tot_out = tot_reason = 0
models = {}
per_run = []
no_usage = []
for n in today:
    p = os.path.join(CR, n)
    txt = read_text(p)
    r_in = r_cached = r_out = r_reason = 0
    found = False
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("type") == "turn.completed" and isinstance(d.get("usage"), dict):
            u = d["usage"]
            r_in += u.get("input_tokens", 0) or 0
            r_cached += u.get("cached_input_tokens", 0) or 0
            r_out += u.get("output_tokens", 0) or 0
            r_reason += u.get("reasoning_output_tokens", 0) or 0
            found = True
        m = re.search(r"Model metadata for `([^`]+)`", json.dumps(d, ensure_ascii=False))
        if m:
            models[m.group(1)] = models.get(m.group(1), 0) + 1
    if not found:
        no_usage.append(n)
    tot_in += r_in; tot_cached += r_cached; tot_out += r_out; tot_reason += r_reason
    per_run.append((n, r_in, r_cached, r_out, r_reason))

print("runs with no turn.completed usage:", len(no_usage), no_usage[:5])
print("models named in error lines:", models)
print()
print("TODAY CODEX TOTALS (JST day 2026-08-07, %d runs):" % len(today))
print("  input_tokens        %12d" % tot_in)
print("  cached_input_tokens %12d  (%.1f%% of input)" % (tot_cached, 100.0*tot_cached/tot_in if tot_in else 0))
print("  fresh input         %12d" % (tot_in - tot_cached))
print("  output_tokens       %12d" % tot_out)
print("  reasoning_output    %12d  (subset of output)" % tot_reason)
print()
print("per-run mean: in %d / out %d" % (tot_in/len(today) if today else 0, tot_out/len(today) if today else 0))
print()
print("last 8 runs (name, in, cached, out, reasoning):")
for row in per_run[-8:]:
    print("  %s  in=%-9d cached=%-9d out=%-6d reason=%d" % row)
