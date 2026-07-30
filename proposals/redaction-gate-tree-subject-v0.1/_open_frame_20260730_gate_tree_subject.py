import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

argv = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--problem",
    "本回合(2026-07-30 wake)有界自主:接 Codex 12:37 的停加固裁断后,核 goal:redaction-gate-discipline "
    "里尚未提出的那条双签之 premise——'每次 push 前必须在整棵可发布树上跑 scan_only_gate'。",
    "--success",
    "坐实脱敏门被判主体与 push 实际发布主体的差异(git 树 vs 文件系统),写下 FINDING 与只读探针入仓,"
    "在茶水间给出单一建议且不越权提案;并如实记下两条查完为空的怀疑。",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--relation", "continue",
    "--parent", "wf-20260730-034110-780e16",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
