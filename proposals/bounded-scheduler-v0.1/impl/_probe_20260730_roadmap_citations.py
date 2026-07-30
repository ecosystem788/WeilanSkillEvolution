# -*- coding: utf-8 -*-
"""只读探针:ROADMAP 在茶水间被引用的时间分布 + 根文档处置状态。
authority: none。不改任何文件。"""
import json, io, subprocess, os

REPO = r"D:\WeilanSkillEvolution"
CHAT = os.path.join(REPO, r"proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl")

print("=== A. ROADMAP 在 peer-chat 里的每一次出现 ===")
n = 0
with io.open(CHAT, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line or "ROADMAP" not in line:
            continue
        n += 1
        try:
            r = json.loads(line)
            t, who = r.get("time"), r.get("from")
            txt = r.get("text", "")
        except Exception:
            t, who, txt = "<parse-err>", "<parse-err>", line
        # 摘出含 ROADMAP 的那一小段
        k = txt.find("ROADMAP")
        snip = txt[max(0, k - 70):k + 120].replace("\n", " ")
        print(f"[{n}] line {i}  {who}  {t}")
        print(f"    ...{snip}...")
print(f"总计 {n} 条\n")

print("=== B. 根目录 .md 的最后一次 commit ===")
docs = ["AGENTS.md", "ARCHITECTURE.md", "CAPABILITY_MAP.md", "CHARTER.md", "CLAUDE.md",
        "EVALUATION_POLICY.md", "LOCAL_STATUS.md", "README.md", "ROADMAP.md",
        "SOLVE_WITH_WEILAN_QUICKSTART.md"]
for d in docs:
    out = subprocess.run(["git", "log", "-1", "--format=%h %ad %s", "--date=short", "--", d],
                         cwd=REPO, capture_output=True)
    line = out.stdout.decode("utf-8", "replace").strip()
    print(f"  {d:36s} {line}")

print("\n=== C. ROADMAP 是否被仓内其他文件引用(非 proposals 历史留痕) ===")
out = subprocess.run(["git", "grep", "-l", "ROADMAP", "--", "*.md", "*.py", "*.json"],
                     cwd=REPO, capture_output=True)
for p in out.stdout.decode("utf-8", "replace").splitlines():
    if p.startswith("proposals/"):
        continue
    print("  ", p)
