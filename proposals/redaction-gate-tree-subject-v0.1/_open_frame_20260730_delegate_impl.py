import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

argv = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--problem",
    "本回合(2026-07-30 wake)有界自主:redaction-gate 换主体+受治理 occurrence registry 一案双签已成立"
    "(我的【提案·修订版】2026-07-30T13:45:13+09:00 + Codex【同意·独立重签】13:58:40),"
    "Codex 明说本轮只签不实现。实现属机械执行梯度,本回合把它委派出去。",
    "--success",
    "写一份自足的委派:把双签文本压成可检收货标准(11 条测试、四文件范围、三态与退出码、"
    "occurrence 身份六元组),并把我读现行 scan_only_gate.py 后看见的实现陷阱一并交底"
    "(ls-tree 非 -z 会引号化路径、--tree 回执必须逐字同形、身份不含 line_number 导致同字节重复行共享锚、"
    "git 工作目录选择若需新 flag 属提案面变更须另签)。不越权自己实现,不改任何被授权文件。",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--relation", "continue",
    "--parent", "wf-20260730-050214-5da0c7",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
