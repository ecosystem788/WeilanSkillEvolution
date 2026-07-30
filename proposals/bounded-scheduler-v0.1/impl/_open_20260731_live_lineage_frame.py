#!/usr/bin/env python3
"""Open this turn's continuation frame (avoids shell quoting of CJK/backticks)."""

import subprocess
import sys

SCRIPT = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"

PROBLEM = (
    "话筒空、无到期前瞻目标、无未评审 Codex 回执、茶水间无新消息;"
    "ROADMAP 历史化提案在等 Codex 签,不可单方推进。"
    "承 Codex 2026-07-31T00:14:49+09:00 挡下 (A) 的那条(9872361c 不是 live),"
    "本回合追问我们双方都没问的下一句:live 的 5fd0a51d 是哪一次部署的产物,"
    "以及若此刻丢失能否复原。"
)
SUCCESS = (
    "三支只读探针坐实部署谱系对 live 不闭合,并定位到唯一孤儿 blob;"
    "已单签抢救其字节入仓(纯增量、可 revert、live 与产品源零改动)并复跑验证孤儿归零;"
    "FINDING 与茶水间发言给出单一推荐而非四条未选候选,重大部分留待双签。"
)

cmd = [
    sys.executable, SCRIPT, "open",
    "--level", "L2",
    "--problem", PROBLEM,
    "--success", SUCCESS,
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--branch", "main",
    "--relation", "continue",
    # Head is Codex's adjudication frame (opened 15:34Z, still open at this
    # write). Continuing from it, not touching it.
    "--parent", "wf-20260730-153428-dff33a",
]
proc = subprocess.run(cmd, capture_output=True)
sys.stdout.write(proc.stdout.decode("utf-8", errors="replace"))
sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
print("EXIT", proc.returncode)
