# -*- coding: utf-8 -*-
"""
只读探针 B:把 wake-entrypoint-ergonomics-v0.1 的 FINDING A(沙箱证明 wake_brief 第二跑烧掉 delta)
放到真实唤醒记录上,量它到底发过没发、发过几次。

主体 = Claude 侧会话转录里,首条 user 消息逐字等于唤醒提示的会话(自主唤醒回合),最近 40 个。
对每个含 >=2 次 wake_brief 调用的回合,逐次取出它的 tool_result,判:
  · 第一次是否成功(失败后重试是正当的,不算损失);
  · 每次的 cursor_status 与各 delta 的条数;
  · 若第一次成功且第二次 delta 全空 —— 记为 burned(真实回合里真的烧掉了增量)。

大输出会被 harness 落盘为 tool-results/*.txt 并在转录里只留预览;
本探针对这种情形如实标 truncated_preview,并在预览里尽力抓 cursor_status/条数,抓不到就标 unknown。
不做任何写入(除同名 .out.json)。
"""
import json, io, os, re, sys

SESSIONS = r"C:\Users\zy\.claude\projects\D--WeilanSkillEvolution"
WAKE_PROMPT = "现在醒来，执行这一回合的自主工作。照系统提示的纪律来。"
N_RECENT = 40
DELTA_KEYS = ("owner_inbox_delta", "prospective_due", "peer_chat_new",
              "codex_replies_unreviewed", "concurrent_receipts_new")
# basename 精确 + 必须带 --workspace:排除 `pytest test_wake_brief.py`(同名副本跑在
# 临时目录、不碰活 cursor)与 `--help`(argparse 先退出,不读 cursor)。
INVOKE_BRIEF = re.compile(r"python[^|;\n]{0,200}?[\\/\"']wake_brief\.py[\"']?[^|;\n]*--workspace")


def result_text(block):
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def parse_brief(text):
    """从 tool_result 文本里尽力抠出 cursor_status 与各 delta 条数。"""
    info = {"cursor_status": None, "delta_counts": {}, "parsed": "none"}
    # 先试整段 JSON
    t = text.strip()
    start = t.find("{")
    if start >= 0:
        try:
            d = json.loads(t[start:])
            info["parsed"] = "full_json"
            cs = d.get("cursor_status")
            info["cursor_status"] = cs if not isinstance(cs, dict) else cs.get("status")
            for k in DELTA_KEYS:
                v = d.get(k)
                if isinstance(v, list):
                    info["delta_counts"][k] = len(v)
            return info
        except Exception:
            pass
    m = re.search(r'"cursor_status"\s*:\s*\{?\s*"?(?:status"\s*:\s*")?([a-z_]+)', text)
    if m:
        info["cursor_status"] = m.group(1)
        info["parsed"] = "regex"
    for k in DELTA_KEYS:
        m2 = re.search(r'"%s"\s*:\s*\[\s*\]' % k, text)
        if m2:
            info["delta_counts"][k] = 0
    if info["parsed"] == "none" and text:
        info["parsed"] = "unstructured"
    return info


def scan_session(path):
    first_user = None
    calls = []            # (tool_use_id, ts, blob)
    results = {}          # tool_use_id -> text
    persisted = {}        # tool_use_id -> saved path if harness persisted it
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
            if typ == "user" and first_user is None and not r.get("isSidechain"):
                c = r.get("message", {}).get("content")
                if isinstance(c, str):
                    first_user = c
            if typ == "assistant" and not r.get("isSidechain"):
                for c in r.get("message", {}).get("content", []) or []:
                    if c.get("type") == "tool_use":
                        inp = c.get("input") if isinstance(c.get("input"), dict) else {}
                        cmd = inp.get("command") or ""
                        # 只认真调用:shell 工具里 `python ... wake_brief.py`。
                        # Write/Edit 里提到同名字符串(探针源码本身就在讨论它)不算。
                        if c.get("name") in ("Bash", "PowerShell") and isinstance(cmd, str) \
                                and INVOKE_BRIEF.search(cmd):
                            calls.append({"id": c.get("id"), "ts": r.get("timestamp"),
                                          "blob": cmd[:300]})
            if typ == "user" and not r.get("isSidechain"):
                c = r.get("message", {}).get("content")
                if isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            txt = result_text(b)
                            results[b.get("tool_use_id")] = txt
                            m = re.search(r"saved to:\s*(\S+)", txt)
                            if m:
                                persisted[b.get("tool_use_id")] = m.group(1)
    return first_user, calls, results, persisted


def main():
    files = [os.path.join(SESSIONS, f) for f in os.listdir(SESSIONS) if f.endswith(".jsonl")]
    files.sort(key=os.path.getmtime)
    exclude = os.environ.get("WEILAN_PROBE_EXCLUDE", "")
    rounds, matched = [], 0
    for path in reversed(files):
        if matched >= N_RECENT:
            break
        if exclude and exclude in path:
            continue
        try:
            fu, calls, results, persisted = scan_session(path)
        except Exception:
            continue
        if fu != WAKE_PROMPT:
            continue
        matched += 1
        if len(calls) < 2:
            continue
        obs = []
        for c in calls:
            txt = results.get(c["id"], "")
            info = parse_brief(txt)
            saved = persisted.get(c["id"])
            if saved and (info["parsed"] in ("none", "unstructured", "regex")) and os.path.exists(saved):
                try:
                    info2 = parse_brief(io.open(saved, encoding="utf-8", errors="replace").read())
                    if info2["parsed"] == "full_json":
                        info = info2
                        info["from_persisted_file"] = saved
                except Exception:
                    pass
            obs.append({
                "ts": c["ts"],
                "result_len": len(txt),
                "harness_persisted": bool(saved),
                "errored": ("error" in txt.lower()[:200] and "cursor" not in txt.lower()[:200]),
                "cursor_status": info["cursor_status"],
                "delta_counts": info["delta_counts"],
                "parsed": info["parsed"],
            })
        first_ok = not obs[0]["errored"] and obs[0]["result_len"] > 0
        later_all_zero = None
        later = obs[1:]
        known = [o for o in later if o["delta_counts"]]
        if known:
            later_all_zero = all(sum(o["delta_counts"].values()) == 0 for o in known)
        rounds.append({
            "session": os.path.basename(path),
            "brief_calls": len(calls),
            "first_call_succeeded": first_ok,
            "later_calls_all_empty_delta": later_all_zero,
            "verdict": ("burned" if (first_ok and later_all_zero) else
                        ("legit_retry" if not first_ok else
                         ("unknown" if later_all_zero is None else "not_burned"))),
            "observations": obs,
        })

    summary = {
        "wake_rounds_scanned": matched,
        "rounds_with_repeat_brief": len(rounds),
        "verdicts": {},
    }
    for r in rounds:
        summary["verdicts"][r["verdict"]] = summary["verdicts"].get(r["verdict"], 0) + 1
    out = {"probe": os.path.basename(__file__), "readonly": True,
           "summary": summary, "rounds": rounds}
    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2)[:6000])
    sys.stdout.write("\nwrote: " + dest + "\n")


if __name__ == "__main__":
    main()
