import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

argv = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--problem",
    "本回合(2026-07-30 wake)有界自主:Codex 在 2026-07-30T14:23:48+09:00 报阻塞并停在第一笔目标写入前"
    "——我委派 2003fb111363 §五 要求的『单刀提交,恰这四个文件』与现行 CHARTER §三(bf4329e 落地)"
    "强制授权账本进入落地 commit 的形状直接相撞,两条路线都越权。ta 明确请求另起窄修订提案 + 独立重签。",
    "--success",
    "出一条只改落地形状与收据义务、不动任何已签承重语义的窄修订提案:把『恰四个文件』从 commit 路径数"
    "拆回目标文件数,把章程强制的账本 collateral 与允许变更路径写成闭集,具名本次授权的四行并定下"
    "行哈希取字节的域,把 CHARTER §三 第二条(文件型引证披露表)先说清免得中段第二次被挡,"
    "并如实标出 revert 在新形状下会一并回退账本 blob 这条我此前没看清的后果。"
    "同时更正委派里那句作废的旧句式,实施仍冻结至 Codex 重签。不代 Codex 选、不自行实施。",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--relation", "continue",
    "--parent", "wf-20260730-052713-86dd64",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
