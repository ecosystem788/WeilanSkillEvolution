"""只读自查：本回合我**新写**的内容是否命中脱敏 registry。

背景：脱敏门 scan_only_gate.py 对 impl 整目录判 FAIL，但那些命中是存量
（已由 goal:redaction-gate-discipline 管着，且新增的 wake-codex-runs/* 不是我写的）。
本自查只回答一个窄问题：**我这一回合追加/新建的内容有没有引入新命中。**

纪律：沿用 scan_only_gate 的 registry 与计数口径（str.count），且**绝不打印任何 pattern**，
只打印命中计数与所在标的。全程只读。
"""
import io
import json
import os
import sys

GATE_DIR = r"D:\WeilanSkillEvolution\proposals\scaffold-opensource-export-v0.1"
sys.path.insert(0, GATE_DIR)
import scan_only_gate as gate  # noqa: E402

private_abs = os.path.abspath(os.path.join(GATE_DIR, gate.DEFAULT_PRIVATE))
patterns, _ruleset_digest = gate.load_patterns(private_abs)

IMPL = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"
QODER = r"D:\WeilanSkillEvolution\proposals\qoder-membership-channel-v0.1"

# 本回合新建的整文件
NEW_FILES = [
    os.path.join(QODER, "FINDING_PROPOSED_API_GATE.md"),
    os.path.join(QODER, "_probe_20260730_proposed_api_gate.py"),
    os.path.join(QODER, "_probe_20260730_proposed_api_gate.out.json"),
    os.path.join(IMPL, "_append_20260730_proposed_api_gate_chat.py"),
    os.path.join(IMPL, "_append_20260730_preauth_convergence.py"),
    os.path.join(IMPL, "_register_20260730_preauth_goal.py"),
]

# 本回合我追加进 peer-chat.jsonl 的行：time 恰为这三个时刻且 from=claude
MY_CHAT_TIMES = {"2026-07-30T19:18:07+09:00", "2026-07-30T19:25:33+09:00"}

report = {"probe": "selfcheck-redaction-new-content-only", "read_only": True,
          "pattern_count": len(patterns), "targets": []}


def count_hits(label, text):
    total = 0
    per = []
    for i, pat in enumerate(patterns):
        c = text.count(pat)
        if c:
            per.append({"pattern_index": i, "count": c})
            total += c
    report["targets"].append({"target": label, "hit_count": total, "hits": per})
    return total


grand = 0
for path in NEW_FILES:
    if not os.path.isfile(path):
        report["targets"].append({"target": path, "hit_count": None,
                                  "note": "missing"})
        continue
    grand += count_hits(os.path.basename(path),
                        io.open(path, encoding="utf-8", errors="replace").read())

# peer-chat：只查我这一回合追加的行
chat = os.path.join(IMPL, "peer-chat.jsonl")
mine = []
for ln in io.open(chat, encoding="utf-8", errors="replace"):
    ln = ln.strip()
    if not ln:
        continue
    try:
        d = json.loads(ln)
    except Exception:
        continue
    if d.get("from") == "claude" and str(d.get("time", "")).startswith("2026-07-30T19:"):
        mine.append(d)
report["my_chat_rows_this_episode"] = [d.get("time") for d in mine]
for d in mine:
    grand += count_hits("peer-chat row time=" + str(d.get("time")), d.get("text", ""))

report["new_content_hit_total"] = grand
report["verdict"] = "PASS" if grand == 0 else "FAIL"
print(json.dumps(report, ensure_ascii=False, indent=2))
