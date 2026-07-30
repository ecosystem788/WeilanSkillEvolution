import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-053611-e85c8d"

AUDIT_REASON = (
    "本回合无 durable 用户指令需入语义记忆:wake_brief owner_inbox_delta=[](话筒无新话),"
    "云自 2026-07-27 未在茶水间发言,本回合未与观察员交互。全部产出已入账本"
    "(peer-chat.jsonl 2026-07-30T14:34:12+09:00、codex-inbox.jsonl id=8f3c21a7d40e)与仓库文件,"
    "承重事实真源是仓库文件与账本,不是 auto-memory。故诚实走 not_persisted。"
)

VERDICT = (
    "做了一件真活并验证:回应 Codex 的阻塞,出了一条只改落地形状、不动任何已签承重语义的窄修订提案。"
    "(1) 醒来状态:activation ACTIVE / control active;wake_brief 一次跑通(cursor incremental),"
    "话筒 delta 空、到期前瞻空、并发收据空;活性哨 appended=[] 无告警"
    "(anchor=codex-inbox-replies.jsonl:106 @2026-07-30T14:24:09+09:00 codex 活动)。"
    "open_agenda 12 条,本回合不动,因为有更高优先的在手事项。"
    "(2) 唯一新差异 = Codex 的阻塞(codex-inbox-replies.jsonl:106 + peer-chat 2026-07-30T14:23:48+09:00):"
    "ta 停在第一笔目标写入前,未改四个目标文件、未跑 11 条测试作完成宣称、未建 landing commit,"
    "理由是我委派 2003fb111363 §五『单刀提交,恰这四个文件』与现行 CHARTER §三 相撞,两条路线都越权。"
    "我回源核了,阻塞成立,错在我这边:CHARTER.md:41-61(bf4329e,2026-07-30T00:07:47+09:00 落地)强制提交前"
    "git add 承载授权的账本,并在 :60-61 明写『落地 commit 因此不再只含目标文件』且『commit 恰 N 文件』"
    "那类旧句式不得沿用——我写的正是那句被明令作废的形状。我不躲在『那只是委派措辞』后面:"
    "13:45:13 §五 与 Codex 同意里的『四文件范围』同样可被读成 commit 路径数,故两个读法一起修。"
    "(3) 本回合唯一新结构:peer-chat.jsonl 2026-07-30T14:34:12+09:00【提案·窄修订】。七节,"
    "全部内容就是把『恰四个文件』从 commit 路径数拆回目标文件数:§一 把目标文件集(恰 4,不可扩)与"
    "章程强制的授权账本 collateral(恰 1 条 peer-chat.jsonl)分开命名,不许互相冒充;"
    "§二 允许变更路径写成闭集 A∪B=5 条,明令不许 git add -A/./commit -a,并声明闭集是允许不是要求;"
    "§三 具名本次授权四行(13:45:13 line-sha256 13fd2830…、13:58:40 cb4ae087…,两行我实测已在"
    "HEAD=a22384c 的账本 blob 内——3062 行 vs 工作树 3063 行;修订提案与重签两行落地时必定未提交,"
    "所以 git add 账本在本案里不是形式主义),并把行哈希取字节的域钉在 <commit>:<path> 的 blob,"
    "明确不许拿工作区字节算(CHARTER.md:55-59 三域不得偷换);§四 收据措辞照新形状重述,"
    "『5 条路径』仍标为自愿核验不是条款。"
    "(4) 两处我主动多做的、都标了层级:§五 把 CHARTER.md:62-75(文件型引证的落地树可见性)先说清——"
    "两条授权都明确声称仓内文件型证据是判断基础,故收据须附逐字保留原始引用字样的披露表;"
    "我只报实测(FINDING.md 今天被跟踪且干净)、把三态分类留给 Codex 现场判,不代判;"
    "并明写这是披露义务不是纳入义务,不许因这张表把证据文件 add 进去变成第 5 个目标文件。"
    "§六 是一条我写修订时才看清的新差异(不改任何签名语义):git revert 那个 commit 会把账本 blob"
    "一并回退到前像,即从树里移除本次一并进来的账本行——不抹掉留痕(行仍在工作树与后续 commit,"
    "账本仍只追加),但 13:45:13 §五 那句『回滚＝revert 那一个 commit』在新形状下不能再被读成"
    "『回滚只影响四个目标文件』。具体回滚做法(整 revert 还是只退 4 个目标文件而留住账本)我明确留白"
    "待回滚那一刻另判,不代选、不塞进本次签名范围。"
    "(5) 顺手把委派侧的死措辞更正:codex-inbox.jsonl id=8f3c21a7d40e,明标『不是新任务』,"
    "作废 2003fb111363 §五 第一句,落地形状改指 14:34:12 那条修订,并明说实施仍冻结至 Codex 重签、"
    "四个目标文件继续不动。这一步的必要性是承重的:那句旧措辞留在收件箱里会让下一次唤醒的 Codex"
    "重新撞上同一堵墙。"
    "(6) 本回合未执行任何被授权的改动:scan_only_gate.py 与三个新文件一字未动、未跑那 11 条测试、"
    "未建 landing commit、未加 --repo。§七 我明写了拒签指引(若本修订实际放宽了任一承重语义、"
    "把 collateral 写成扩项偷渡口、或 §五 披露义务超出窄修订范围而该另案,请【反对】或只签认的部分)。"
    "(7) 过程中一处纠错:open --parent 先用 Codex 的 wf-20260730-052028-5084e5 被 head 冲突挡下;"
    "show 后确认真 head wf-20260730-052713-86dd64 是调度器自己的 wake 收据帧(frame_opened→frame_closed"
    "两事件、problem=bounded-scheduler wake episode、已 closed),不是并发工作者,遂改对再开。"
    "另记两处工具形状:weilan_trace show 不接 --workspace/--scope(接了报 unrecognized arguments),"
    "且返回的是事件数组不是对象。"
    "下一回合从哪续:读 peer-chat.jsonl 看 Codex 对 14:34:12 窄修订的判——【同意】则实施解冻"
    "(仍由 Codex 做,评审是我的梯度:回源核目标文件恰四个、账本作为第 5 条路径进来、11 条逐条报名带结果"
    "不接受只报 11 passed、registry 确为空、ls-tree 是否用了 -z 拿那 15 条非 ASCII 路径实测、"
    "--tree 回执字节级同形、有没有偷加 --repo、以及披露表与四行行哈希是否齐);"
    "【反对】则按 ta 的理由再收窄,不还嘴、不绕行。未回则如实记 still-pending,不代做、不自行放宽。"
    "goal:redaction-gate-tree-subject-proposal 保持 ACTIVE,它现在承载的是『修订被独立重签且实施到货并被验收』。"
    "云那条待裁(两处已公开命中:留着不动 vs 重写公开历史)仍不催不代判。"
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
    sys.stdout.write(proc.stdout.decode("utf-8", "replace")[:400] + "\n")
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        sys.exit(proc.returncode)
