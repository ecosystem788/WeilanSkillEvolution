import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

DESCRIPTION = (
    "我在 2026-07-30T12:54:42+09:00 的茶水间【FINDING·不开案｜push 前脱敏门判的不是 push 会发布的那棵树】"
    "第五节里公开说了『四条候选我刻意不选,留给你独立判』并给了单一建议『下一轮由我起窄提案』——"
    "这个目标就是不让那句话蒸发。\n\n"
    "已坐实的事实(全文 proposals/redaction-gate-tree-subject-v0.1/FINDING.md,只读探针与其输出在同目录,"
    "口径写在第二节;测于 HEAD=225a0d0,被判 commit=310e5754 即 2026-07-30 日推的 authorized head):"
    "scan_only_gate.py 的 --tree 是文件系统目录并 os.walk,而 push 发布的是 git 树。同一 pattern 表/decode 规则/"
    "SKIP_DIRS 下,git 树 3921 路径 2 命中,文件系统 36759 文件 163 命中;filesystem_only=161、git_tree_only=0,"
    "且那 161 个里在被判 commit 上被跟踪的是 0 个。故今天没有第三处泄露(07-30 06:38:05 报给云的两处对已发布树"
    "是准确的),但门的 FAIL 里 98.8% 与是否发布无关。三条附加事实:门读工作区脏字节(此刻 15 个 dirty 被跟踪文件,"
    "peer-chat.jsonl 在内),两主体今天同答是偶合不是结构保证;被判主体本身漂移(本回合 36762→36759,"
    "差额恰是我建了又删的 3 个临时文件);.gitignore 不是判据——wake-codex-runs/ 与 wake-agent-runs/ 同被 ignore,"
    "该 commit 上跟踪数却是 0 对 1035(ignore 不追溯既已跟踪路径)。\n\n"
    "本目标要做的事:起一条窄【提案】,范围锁 proposals/scaffold-opensource-export-v0.1/scan_only_gate.py "
    "与其测试,主体从文件系统换成 authorized oid 上的 git 树(--tree 保留给 export 原用途),并加已公开命中的锚集"
    "以区分『零新增暴露』与『干净』两态,锚集须自带一条『谁能往里加』的准入规矩否则它是消音器。\n\n"
    "醒来后先回源核验三件事,任一不满足就不要照原样提:(1) Codex 是否已对该 FINDING 独立判过并选了候选"
    "——我在发言里明说了『这轮我不提,先要你独立判过』,ta 未判则不得代判,如实记 still-pending 并退出;"
    "(2) 云对 goal:redaction-gate-discipline 第 (1) 项(两行已公开命中:留着不动 vs 重写公开历史)是否已裁断"
    "——不催不代判,四条候选在两种裁断下都成立,故此项不构成阻塞;(3) 门与探针是否有漂移,有则重跑探针再说。\n\n"
    "与既有目标的关系(刻意声明重叠而不藏):本目标是 goal:redaction-gate-discipline 的**伴生**而非替代。"
    "那条仍持有云的待裁席位;本条只接管它第 (2) 项『每次 push 前必须在整棵可发布树上跑 scan_only_gate』的双签,"
    "并携带一条更正——那句话里的『整棵可发布树』在今天的器械上没有对应主体,所以**不该照原话提**。"
)

argv = [
    sys.executable, TRACE, "prospective-register",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--goal-ref", "goal:redaction-gate-tree-subject-proposal",
    "--description", DESCRIPTION,
    "--event-kind", "clock",
    "--event-name", "gate-subject-proposal-window",
    "--not-before", "2026-07-30T05:30:00+00:00",
    "--death-line",
    "collapse if not completed by 2026-08-06T15:00:00+00:00",
    "--source", "frame:wf-20260730-035637-9fc8ad",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
