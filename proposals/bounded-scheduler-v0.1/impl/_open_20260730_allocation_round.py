"""Open this round's receipt frame. Written as a script so the Chinese text and
any backticks reach python unmangled by the shell."""
import subprocess
import sys

TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"

PROBLEM = (
    "云 2026-07-30 21:39:39 在茶水间问:这两天做的事是沿着收益明确且较大的方向,"
    "还是挖掘过细、进度平缓?本回合的活是不凭感觉答——用只读可复跑的量测清产能分配,"
    "如实回云,并把由此得出的纪律改动正式提交同行双签。"
)
SUCCESS = (
    "四个量各自独立取证且可只读复跑(commit 路径归并 / evals-tests-skill 自 07-20 起为空 / "
    "活体技能 mtime / prospective 队列 14 ACTIVE 中 11 条同形状);茶水间落两条:"
    "对云一条(短、非程序员可读、单一推荐路径)与对 Codex 一条【提案】(含改什么·解除条件·"
    "怎么验证·怎么回滚·三条边界);提案不在本回合执行,等同行签名。"
)

cmd = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--problem", PROBLEM,
    "--success", SUCCESS,
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--branch", "main",
    "--relation", "continue",
    "--parent", "wf-20260730-123710-59b1b4",
]
proc = subprocess.run(cmd, capture_output=True)
print("rc", proc.returncode)
print(proc.stdout.decode("utf-8", "replace")[:2000])
print("STDERR", proc.stderr.decode("utf-8", "replace")[:2000])
