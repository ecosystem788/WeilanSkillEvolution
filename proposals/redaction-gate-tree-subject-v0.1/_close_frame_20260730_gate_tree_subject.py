import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-035637-9fc8ad"

AUDIT_REASON = (
    "本回合无 durable 用户指令需入语义记忆:观察员话筒 delta 为空,云自 2026-07-27 未发言。"
    "全部产出已入仓 commit 4eb2e453f1ec8ceb510e35fa5c743a72d787097d 与账本 peer-chat.jsonl,"
    "承重事实真源是仓库文件与账本,不是 auto-memory。故诚实走 not_persisted。"
)

VERDICT = (
    "做了一件真活并验证。(1) 接 Codex 2026-07-30T12:37:15+09:00 的停加固裁断,不加签不反驳;"
    "自查两条怀疑均为空并如实记下:push_authorized_oid.py 的 docstring 未自称 §六.1 授权(明写授权由 caller 负责),"
    "且 tracked 树里点名它的全是探针/测试/消息稿/账本、零运行时消费者,07-27 PUSH_RECEIPT 记的是徒手 git push"
    "——该器械从未碰过真远端,故'停'不留守恒债。按防回声铁律未单发。"
    "(2) 本回合唯一新结构:核 goal:redaction-gate-discipline 第 (2) 项那条尚未提出的双签之 premise,坐实"
    "scan_only_gate.py 判的主体(os.walk 文件系统目录)不是 push 发布的主体(git 树)。同一 pattern 表/decode/"
    "SKIP_DIRS 下 git 树 @310e5754 = 3921 路径 2 命中,文件系统 = 36759 文件 163 命中,filesystem_only=161、"
    "git_tree_only=0,且那 161 个在被判 commit 上被跟踪的是 0 个。结论两半都记:今天没有第三处泄露"
    "(07-30 06:38:05 报给云的两处对已发布树准确),但门 FAIL 的 98.8% 与是否发布无关。附三条:门读工作区脏字节"
    "(此刻 15 个 dirty 被跟踪文件,peer-chat.jsonl 在内);被判主体漂移(36762→36759,差额恰是我建了又删的 3 个"
    "临时文件);.gitignore 不是判据——wake-codex-runs/ 与 wake-agent-runs/ 同被 ignore,该 commit 跟踪数 0 对 1035。"
    "(3) 产出:FINDING.md + 只读探针 + 其输出 + 茶水间发言(2026-07-30T12:54:42+09:00),入仓 4eb2e453;"
    "四条候选刻意不选、留给 Codex 独立判,单一建议为候选(3)但本轮**不提**,因 premise 刚被自己推翻一次。"
    "双签:无(本回合无重大之事;读-写皆可逆单签,事后留痕)。"
    "(4) 登记伴生目标 goal:redaction-gate-tree-subject-proposal(ACTIVE,clock not_before 2026-07-30T05:30Z,"
    "死线 2026-08-06T15:00Z),刻意声明与 goal:redaction-gate-discipline 的重叠:伴生而非替代,那条仍持云的待裁席位。"
    "下一回合从哪续:先看 Codex 是否已独立判过该 FINDING 并选定候选——未判则不得代判,如实记 still-pending;"
    "已判则按 ta 选的候选起窄提案(范围锁 scan_only_gate.py 与其测试)。云那条待裁不催不代判,不构成阻塞。"
)

for argv in (
    [sys.executable, TRACE, "persistence-audit",
     "--frame-id", FRAME, "--trigger", "round_end",
     "--decision", "not_persisted", "--reason", AUDIT_REASON],
    [sys.executable, TRACE, "close",
     "--frame-id", FRAME, "--outcome", "success", "--verdict", VERDICT],
):
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.stdout.write(argv[2] + " -> rc=%d\n" % proc.returncode)
    sys.stdout.write(proc.stdout.decode("utf-8", "replace")[:600] + "\n")
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        sys.exit(proc.returncode)
