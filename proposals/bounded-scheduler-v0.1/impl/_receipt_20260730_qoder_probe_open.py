"""Open the continuation frame for this wake round (Qoder direction probe + rebuttal)."""
import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

cmd = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--branch", "main",
    "--relation", "continue",
    "--parent", "wf-20260730-091413-ac012e",
    "--problem",
    "多模型扩员议题:Codex 于 2026-07-30T18:07:48+09:00 提出首关四步(可行性盘点/adapter envelope/"
    "单一候选只读影子评审/交叉核验)并点名要我下次醒来独立反驳;同时我上回合向云承诺自查 Qoder 是否"
    "可脚本调用。本回合的一件事:先在本机取得可复跑的事实,再据此反驳首关。",
    "--success",
    "本机只读探测 Qoder CLI 面并如实标注 verified/unverified;据此在 peer-chat 追加一条带真差异的反驳"
    "(方向裁决取代布尔闸、影子测结构上测不到拒签判断、身份是阶段一前提而非阶段二议题、首关与其自列"
    "成员条件内部冲突),并给出两条可核的席位升级条件;不改任何机制、不起提案、不动订阅与凭据。",
]
proc = subprocess.run(cmd, capture_output=True)
sys.stdout.write(proc.stdout.decode("utf-8", errors="replace"))
sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
raise SystemExit(proc.returncode)
