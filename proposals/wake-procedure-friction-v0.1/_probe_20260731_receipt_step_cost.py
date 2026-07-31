# -*- coding: utf-8 -*-
"""
只读探针 C:摩擦落在哪一步 —— 量"出收据"这一步的真实代价。

来路:探针 A 报告有 1/40 回合缺收据。回源核验发现那不是遗漏 —— 那一回合是**先写了一个
一次性 Python 包装脚本**(_open_frame_*.py / _close_frame_*.py)再跑它来开/闭帧,
CLI 从未直接出现。误判由此而来,并直接指出真正的观测量:

    一个步骤,若使用者需要**先写一个程序**才能执行它,那就是这个器官最硌手的地方。

本探针对最近 40 个自主唤醒回合量:
  · 收据相关调用数(直接 CLI + 包装脚本的 Write/Edit + 跑包装脚本);
  · 占该回合全部工具调用的比例;
  · 有多少回合用了"写包装脚本"这条路,而不是直接敲命令。
只读,除同名 .out.json 外无写入。
"""
import json, io, os, re, sys, statistics

SESSIONS = r"C:\Users\zy\.claude\projects\D--WeilanSkillEvolution"
WAKE_PROMPT = "现在醒来，执行这一回合的自主工作。照系统提示的纪律来。"
N_RECENT = 40

# 直接 CLI 分两类:
#  lifecycle = 真正写收据的动作(open / close / persistence-audit)
#  inspect   = 为了写收据而必须先做的查询(head-show / show —— 拿 --parent 要用)
# 分开记,免得把"查"算进"写"里虚增代价;两个口径都报,让读的人自己判。
RX_CLI_LIFECYCLE = re.compile(r"weilan_trace\.py[\"']?\s+(?:frame-)?"
                              r"(?:open|close|persistence-audit|persistence-audit-show)\b")
RX_CLI_INSPECT = re.compile(r"weilan_trace\.py[\"']?\s+(?:head-show|show)\b")
# 包装脚本的文件名形态(本仓惯例:_open_frame_*.py / _close_frame_*.py / _receipt_*.py)
RX_WRAPPER_PATH = re.compile(r"_(?:open|close)_frame[^\\/]*\.py$|_receipt[^\\/]*\.py$"
                             r"|_frame_(?:open|close)[^\\/]*\.py$", re.I)
# 包装脚本正文里出现帧生命周期动作(用于确认它确实是在出收据)
RX_WRAPPER_BODY = re.compile(r"frame_open|frame_close|persistence_audit|\"open\"|'open'"
                             r"|command_open|weilan_trace", re.I)


def basename(p):
    return (p or "").replace("\\", "/").rsplit("/", 1)[-1]


def scan(path):
    first_user = None
    calls = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") == "user" and first_user is None and not r.get("isSidechain"):
            c = r.get("message", {}).get("content")
            if isinstance(c, str):
                first_user = c
        if r.get("type") == "assistant" and not r.get("isSidechain"):
            for c in r.get("message", {}).get("content", []) or []:
                if c.get("type") == "tool_use":
                    inp = c.get("input") if isinstance(c.get("input"), dict) else {}
                    calls.append({
                        "tool": c.get("name"),
                        "cmd": inp.get("command") if isinstance(inp.get("command"), str) else "",
                        "file_path": inp.get("file_path") if isinstance(inp.get("file_path"), str) else "",
                        "content": (inp.get("content") or inp.get("new_string") or "")
                                   if isinstance(inp.get("content") or inp.get("new_string"), str) else "",
                    })
    return first_user, calls


def analyse(calls):
    wrapper_names = set()
    tagged = []
    for c in calls:
        kind = None
        if c["tool"] in ("Write", "Edit") and RX_WRAPPER_PATH.search(basename(c["file_path"])) \
                and RX_WRAPPER_BODY.search(c["content"] or ""):
            kind = "wrapper_authoring"
            wrapper_names.add(basename(c["file_path"]))
        elif c["tool"] in ("Bash", "PowerShell") and c["cmd"]:
            if RX_CLI_LIFECYCLE.search(c["cmd"]):
                kind = "cli_lifecycle"
            elif RX_CLI_INSPECT.search(c["cmd"]):
                kind = "cli_inspect"
        tagged.append(kind)
    # 第二遍:跑包装脚本的调用(须在它被写出之后才认得出名字)
    for i, c in enumerate(calls):
        if tagged[i] is None and c["tool"] in ("Bash", "PowerShell") and c["cmd"]:
            if any(n in c["cmd"] for n in wrapper_names):
                tagged[i] = "wrapper_run"
    return tagged, wrapper_names


def main():
    files = [os.path.join(SESSIONS, f) for f in os.listdir(SESSIONS) if f.endswith(".jsonl")]
    files.sort(key=os.path.getmtime)
    exclude = os.environ.get("WEILAN_PROBE_EXCLUDE", "")
    rounds = []
    for path in reversed(files):
        if len(rounds) >= N_RECENT:
            break
        if exclude and exclude in path:
            continue
        try:
            fu, calls = scan(path)
        except Exception:
            continue
        if fu != WAKE_PROMPT or not calls:
            continue
        tagged, wrappers = analyse(calls)
        counts = {}
        for t in tagged:
            if t:
                counts[t] = counts.get(t, 0) + 1
        receipt_calls = sum(counts.values())
        strict = receipt_calls - counts.get("cli_inspect", 0)
        rounds.append({
            "session": os.path.basename(path),
            "total_calls": len(calls),
            "receipt_calls": receipt_calls,
            "receipt_calls_strict_no_inspect": strict,
            "breakdown": counts,
            "used_wrapper": counts.get("wrapper_authoring", 0) > 0,
            "wrapper_files": sorted(wrappers),
            "receipt_share_of_calls": round(receipt_calls / len(calls), 4),
        })

    shares = [r["receipt_share_of_calls"] for r in rounds]
    rc = [r["receipt_calls"] for r in rounds]
    rcs = [r["receipt_calls_strict_no_inspect"] for r in rounds]
    wrapper_rounds = [r for r in rounds if r["used_wrapper"]]
    summary = {
        "wake_rounds": len(rounds),
        "receipt_calls_per_round": {
            "median": statistics.median(rc) if rc else None,
            "mean": round(statistics.mean(rc), 2) if rc else None,
            "min": min(rc) if rc else None, "max": max(rc) if rc else None,
        },
        "receipt_calls_per_round_strict_no_inspect": {
            "median": statistics.median(rcs) if rcs else None,
            "mean": round(statistics.mean(rcs), 2) if rcs else None,
            "min": min(rcs) if rcs else None, "max": max(rcs) if rcs else None,
        },
        "receipt_share_of_all_calls": {
            "median": round(statistics.median(shares), 4) if shares else None,
            "mean": round(statistics.mean(shares), 4) if shares else None,
            "max": round(max(shares), 4) if shares else None,
        },
        "rounds_using_a_wrapper_script": len(wrapper_rounds),
        "wrapper_round_rate": round(len(wrapper_rounds) / len(rounds), 4) if rounds else None,
        "distinct_wrapper_files": sorted({w for r in wrapper_rounds for w in r["wrapper_files"]}),
    }
    out = {"probe": os.path.basename(__file__), "readonly": True,
           "summary": summary, "rounds": rounds}
    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write("\nwrote: " + dest + "\n")


if __name__ == "__main__":
    main()
