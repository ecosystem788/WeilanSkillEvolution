# -*- coding: utf-8 -*-
"""
只读探针:量"醒来程序"本身的摩擦。

主体 = Claude 侧会话转录 C:\\Users\\zy\\.claude\\projects\\D--WeilanSkillEvolution\\*.jsonl 中,
首条 user 消息逐字等于唤醒提示的那些会话(= 自主唤醒回合)。

量什么(每个回合):
  · 仪式调用(唤醒提示强制的程序步骤:recall / wake_brief / peer_health / prospective-show / 收据三步)
    的次数与重复次数;
  · 第一次"真活"工具调用之前,烧掉了多少工具调用、多少 assistant output_tokens、多少墙钟时间;
  · 哪些强制步骤在这一回合完全没留痕(遗漏普查);
  · 仪式产物的"消费尾巴"(启发式,已标注):紧随仪式调用之后、用于把它的输出读进来的额外调用。

不做任何写入。不读会话正文以外的东西。输出 JSON 到同名 .out.json。
"""
import json, io, os, re, sys, statistics, hashlib

SESSIONS = r"C:\Users\zy\.claude\projects\D--WeilanSkillEvolution"
WAKE_PROMPT = "现在醒来，执行这一回合的自主工作。照系统提示的纪律来。"
N_RECENT = 40

# 仪式步骤 = 唤醒提示逐条点名、每回合都要做的程序动作
CEREMONY = ("recall", "wake_brief", "peer_health", "prospective_show", "receipt")
MANDATED = ("recall", "wake_brief", "peer_health", "receipt")  # 提示里无条件要求的四步


SHELL_TOOLS = ("Bash", "PowerShell")
# 仪式判据必须是**真调用**,不是"提到"。只在 shell 工具的 command 字段上匹配
# `python ... <script>` 形态;Write/Edit 里出现同名字符串(例如探针源码本身
# 就在讨论 wake_brief.py)一律不算 —— 这是本探针第一版的错,已修。
# 第二次收窄:basename 必须精确(前面须是路径分隔符或引号,否则 `test_wake_brief.py`
# 这类被 pytest 跑的副本会被误算成真调用),且必须带 --workspace(排除 --help)。
INVOKE = {
    "recall": re.compile(r"weilan_trace\.py[\"']?\s+memory-recall\b"),
    "wake_brief": re.compile(r"python[^|;\n]{0,200}?[\\/\"']wake_brief\.py[\"']?[^|;\n]*--workspace"),
    "peer_health": re.compile(r"python[^|;\n]{0,200}?[\\/\"']peer_health_wake\.py[\"']?[^|;\n]*--root"),
    "prospective_show": re.compile(r"weilan_trace\.py[\"']?\s+prospective-show\b"),
    "receipt": re.compile(r"weilan_trace\.py[\"']?\s+(?:frame-)?(?:open|close|persistence-audit)\b"
                          r"|concurrent_receipt_append|concurrent-receipt-append"),
}


def classify(name, inp):
    """把一次 tool_use 归类。返回 (step, is_ceremony)。"""
    inp = inp if isinstance(inp, dict) else {}
    cmd = inp.get("command") or ""
    if name in SHELL_TOOLS and isinstance(cmd, str):
        for step, rx in INVOKE.items():
            if rx.search(cmd):
                return step, True
    blob = json.dumps(inp, ensure_ascii=False).lower()
    if "owner-inbox" in blob:
        return "channel_inbox", False
    if "peer-chat" in blob or "codex-inbox" in blob:
        return "channel_peer", False
    return "work", False


def consumption_tail(calls, i):
    """启发式:第 i 次仪式调用之后,紧接着有几次调用是在'把它的输出读进来'。
    判据 = 之后连续的调用里,输入里出现该仪式产物特征词(_recall/_wake_brief/_brief/read_brief)
    或是对刚写下的读取脚本的运行;一旦出现真活或别的仪式即停。"""
    markers = ("_recall", "recall_", "wake_brief", "_brief", "read_brief", "tool-results")
    tail = 0
    for j in range(i + 1, min(i + 5, len(calls))):
        step, cer = calls[j]["step"], calls[j]["ceremony"]
        if cer or step == "work" and not any(m in calls[j]["blob"].lower() for m in markers):
            break
        if any(m in calls[j]["blob"].lower() for m in markers):
            tail += 1
        else:
            break
    return tail


def read_session(path):
    first_user = None
    events = []
    seen_msg_ids = set()
    out_tokens = 0
    calls = []
    t0 = None
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            typ = r.get("type")
            ts = r.get("timestamp")
            if typ == "user" and first_user is None and not r.get("isSidechain"):
                c = r.get("message", {}).get("content")
                if isinstance(c, str):
                    first_user = c
                    t0 = ts
            if typ == "assistant" and not r.get("isSidechain"):
                m = r.get("message", {})
                mid = m.get("id")
                u = m.get("usage") or {}
                if mid and mid not in seen_msg_ids:
                    seen_msg_ids.add(mid)
                    out_tokens += int(u.get("output_tokens") or 0)
                for c in m.get("content", []) or []:
                    if c.get("type") == "tool_use":
                        step, cer = classify(c.get("name"), c.get("input"))
                        calls.append({
                            "name": c.get("name"),
                            "step": step,
                            "ceremony": cer,
                            "ts": ts,
                            "tokens_so_far": out_tokens,
                            "blob": json.dumps(c.get("input"), ensure_ascii=False)[:400],
                        })
    return first_user, t0, calls, out_tokens


def iso_delta_s(a, b):
    import datetime
    if not a or not b:
        return None
    f = "%Y-%m-%dT%H:%M:%S.%fZ"
    try:
        return (datetime.datetime.strptime(b, f) - datetime.datetime.strptime(a, f)).total_seconds()
    except Exception:
        return None


def main():
    files = [os.path.join(SESSIONS, f) for f in os.listdir(SESSIONS) if f.endswith(".jsonl")]
    files.sort(key=os.path.getmtime)
    current = os.environ.get("WEILAN_PROBE_EXCLUDE", "")
    rounds = []
    scanned = 0
    for path in reversed(files):
        if len(rounds) >= N_RECENT:
            break
        if current and current in path:
            continue
        scanned += 1
        try:
            fu, t0, calls, out_tokens = read_session(path)
        except Exception as e:
            continue
        if fu != WAKE_PROMPT:
            continue
        if not calls:
            rounds.append({"session": os.path.basename(path), "empty": True,
                           "total_calls": 0, "output_tokens": out_tokens})
            continue
        first_work = None
        for i, c in enumerate(calls):
            if c["step"] == "work":
                first_work = i
                break
        step_counts = {}
        for c in calls:
            step_counts[c["step"]] = step_counts.get(c["step"], 0) + 1
        tails = {}
        for i, c in enumerate(calls):
            if c["ceremony"]:
                t = consumption_tail(calls, i)
                if t:
                    tails[c["step"]] = tails.get(c["step"], 0) + t
        rec = {
            "session": os.path.basename(path),
            "start": t0,
            "total_calls": len(calls),
            "output_tokens": out_tokens,
            "step_counts": step_counts,
            "ceremony_calls": sum(1 for c in calls if c["ceremony"]),
            "consumption_tails": tails,
            "missing_mandated": [s for s in MANDATED if step_counts.get(s, 0) == 0],
            "repeated_ceremony": {s: step_counts[s] for s in CEREMONY
                                  if step_counts.get(s, 0) > 1},
        }
        if first_work is None:
            rec["first_work_index"] = None
            rec["calls_before_first_work"] = len(calls)
            rec["tokens_before_first_work"] = out_tokens
            rec["seconds_to_first_work"] = None
            rec["no_work_this_round"] = True
        else:
            rec["first_work_index"] = first_work
            rec["calls_before_first_work"] = first_work
            rec["tokens_before_first_work"] = calls[first_work]["tokens_so_far"]
            rec["seconds_to_first_work"] = iso_delta_s(t0, calls[first_work]["ts"])
            rec["no_work_this_round"] = False
        rec["first_work_preview"] = (calls[first_work]["blob"][:160]
                                     if first_work is not None else None)
        rounds.append(rec)

    live = [r for r in rounds if not r.get("empty") and not r.get("no_work_this_round")]

    def frac(r):
        return (r["tokens_before_first_work"] / r["output_tokens"]) if r["output_tokens"] else None

    fracs = [frac(r) for r in live if frac(r) is not None]
    calls_before = [r["calls_before_first_work"] for r in live]
    omissions = {}
    for r in rounds:
        for s in r.get("missing_mandated", []):
            omissions[s] = omissions.get(s, 0) + 1
    repeats = {}
    for r in rounds:
        for s, n in (r.get("repeated_ceremony") or {}).items():
            repeats.setdefault(s, []).append(n)
    tails_total = {}
    for r in rounds:
        for s, n in (r.get("consumption_tails") or {}).items():
            tails_total[s] = tails_total.get(s, 0) + n

    summary = {
        "sessions_scanned": scanned,
        "wake_rounds_matched": len(rounds),
        "rounds_with_work": len(live),
        "rounds_without_any_work_call": sum(1 for r in rounds if r.get("no_work_this_round")),
        "calls_before_first_work": {
            "median": statistics.median(calls_before) if calls_before else None,
            "mean": round(statistics.mean(calls_before), 2) if calls_before else None,
            "min": min(calls_before) if calls_before else None,
            "max": max(calls_before) if calls_before else None,
        },
        "output_token_fraction_before_first_work": {
            "median": round(statistics.median(fracs), 4) if fracs else None,
            "mean": round(statistics.mean(fracs), 4) if fracs else None,
            "min": round(min(fracs), 4) if fracs else None,
            "max": round(max(fracs), 4) if fracs else None,
        },
        "mandated_step_omissions": omissions,
        "mandated_step_omission_rate": {k: round(v / len(rounds), 4) for k, v in omissions.items()},
        "ceremony_repeat_rounds": {k: len(v) for k, v in repeats.items()},
        "consumption_tail_calls_total": tails_total,
    }
    out = {"probe": os.path.basename(__file__), "readonly": True,
           "sessions_dir": SESSIONS, "wake_prompt_sha256":
           hashlib.sha256(WAKE_PROMPT.encode("utf-8")).hexdigest(),
           "n_recent_requested": N_RECENT,
           "summary": summary, "rounds": rounds}
    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write("\nwrote: " + dest + "\n")


if __name__ == "__main__":
    main()
