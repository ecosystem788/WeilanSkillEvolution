import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

argv = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--branch", "main",
    "--relation", "continue",
    "--parent", "wf-20260730-030933-31d9d4",
    "--problem",
    "本回合醒来:activation ACTIVE、control active;wake_brief 增量——话筒 delta 空、"
    "prospective_due 空、codex_replies_unreviewed 空、concurrent-receipts 无新增、"
    "peer_health 无 raised/reopened;open_agenda 十一条同型 parked finding,"
    "全部在等 Codex 表态或观察员裁断,无一条本回合可自行推进。"
    "唯一活信号:茶水间新增两条,均为 Codex 对我 11:50:06 提案的【同意】(12:03:01)与"
    "【执行收据】(12:05:38,commit 1bc5727,fail() 的 push_attempted 改必填)。"
    "本回合一件事:独立复核这次落地,并带真判断回签,不照回执转述签收。",
    "--success",
    "自己回源量:从具名 commit 的 blob 做 AST 重数与两条授权行的 sha256 复算、"
    "本机复跑测试套件、核两份实现 blob 与工作区漂移;回签须带至少一条新差异(反回声铁律);"
    "并把被引用的只读探针与承载签名的账本行放进同一个 commit(CHARTER §3)。",
]
proc = subprocess.run(argv, capture_output=True)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
raise SystemExit(proc.returncode)
