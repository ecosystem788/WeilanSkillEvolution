import json
import subprocess
import sys

TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"

argv = [
    sys.executable,
    TRACE,
    "open",
    "--level",
    "L2",
    "--problem",
    "回合 2026-07-31 00:2x:核验 Codex 对当前 live 件身份的【反对】,并出 ROADMAP 历史化提案三版",
    "--success",
    "live tree hash 走独立只读路径复量并与 Codex 结论逐字比对;三版文本把 (A)(B) 两处按其要求收窄;新差异(若有)以可核判别量入账;ROADMAP.md 零改动直到双签",
    "--workspace",
    r"D:\WeilanSkillEvolution",
    "--scope",
    "skill-evolution",
    "--branch",
    "main",
    "--relation",
    "continue",
    "--parent",
    "wf-20260730-151808-56dbbb",
]
p = subprocess.run(argv, capture_output=True)
out = p.stdout.decode("utf-8", "replace")
err = p.stderr.decode("utf-8", "replace")
print("rc", p.returncode)
print("STDOUT:", out[:3000])
print("STDERR:", err[:2000])
