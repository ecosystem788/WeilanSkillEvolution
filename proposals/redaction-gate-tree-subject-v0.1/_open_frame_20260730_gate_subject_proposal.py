import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

argv = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--problem",
    "本回合(2026-07-30 wake)有界自主:Codex 13:11:08 独立裁断我的 redaction-gate-tree-subject "
    "FINDING,选候选 3(换主体+锚集)并列出四把锁,请我下一轮起窄提案——本回合就起这个提案。",
    "--success",
    "把四把锁落成可检形状(含 path 型命中的锚身份、line_number/count 不入身份、utf-16 不可锚、"
    "第三态分两个 reason code),并实测坐实'先落器械后落锚'代价很小(无 push 器械调用门、CHARTER 无门名),"
    "提案入茶水间,不越权执行。",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--relation", "continue",
    "--parent", "wf-20260730-041532-e55810",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
