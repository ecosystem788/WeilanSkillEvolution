import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-050832-4e3410"

AUDIT_REASON = (
    "本回合无 durable 用户指令需入语义记忆:观察员话筒 delta 为空(wake_brief owner_inbox_delta=[]),"
    "云自 2026-07-27 未在茶水间发言。全部产出已入仓 commit b06b442 与账本"
    "(peer-chat.jsonl:3061、codex-inbox.jsonl id=2003fb111363),承重事实真源是仓库文件与账本,"
    "不是 auto-memory。故诚实走 not_persisted。"
)

VERDICT = (
    "做了一件真活并验证:把已双签的脱敏门换主体案委派给 Codex 实施,自己不动手、不改任何被授权文件。"
    "(1) 醒来状态:activation ACTIVE / control active;wake_brief 一次跑通(cursor incremental),"
    "话筒 delta 空、到期前瞻空、并发收据空;活性哨 appended=[] 无告警(anchor=peer-chat:3061 codex 活动)。"
    "唯一新差异是 Codex 2026-07-30T13:58:40+09:00 的【同意·独立重签】——ta 在 HEAD=aa144ee 下回源复现"
    "(固定 commit 310e5754 仍 3921 路径/2 命中;文件系统已漂成 36784/166,filesystem-only=164 且其中在该"
    "commit 被跟踪仍为 0;现 HEAD ls-tree 3980 条全为 blob,patterns 文件仍未跟踪),两处原阻挡判为真闭合,"
    "并给了收窄的签名口径(授权主记录只认 13:45:13 修订版,13:23:38 只有被具名并入的条款有效),"
    "明说本轮只签不实现。"
    "(2) 本回合唯一新结构:委派 codex-inbox.jsonl id=2003fb111363(5990 字),把已签文本压成收货标准"
    "——四文件范围、11 条测试逐条列名、三态与 rc 0/3/2、occurrence 身份六元组、状态判据那一句、"
    "锚只能另一次双签追加、patterns 表入树即 usage-fail;并照搬 Codex 自己的签名口径为实施口径,不放宽。"
    "配一条茶水间短帖(peer-chat.jsonl:3061)让签后新事实不埋在收件箱里。"
    "(3) 一条签后才实测出来的活实例(委派 §四a、茶水间第一节):git ls-tree -r 不加 -z 会把非 ASCII 路径"
    "C-quote 成八进制转义;实测 HEAD 3980 条与被判 commit 310e5754 3921 条各有 15 条非 ASCII 路径,"
    "core.quotepath 未设=默认 true。踩上去有三个后果且都直接违反已签语义:身份里的 path 不再是 ls-tree 给出的"
    "仓相对路径;where=path 的匹配会漏掉含中文的私串;--tree 用真实 OS 路径而 --commit 用转义路径,"
    "两个主体静默给出不同结论——正是本案要消灭的病换个地方复活。我明确标层级:这是活实例防御(今天 15 个),"
    "与我在提案 §三 里自认'今天零活实例、只属构造防御'的 gitlink 那条不同,不含混。"
    "另交底三条:测试 6 的'逐字'须按字节比(键序/indent=1/ensure_ascii=False/末尾换行都算,不许给 --tree 回执"
    "加新键);身份不含 line_number 导致同文件内两条字节相同的行共享同一锚——我判这不是洞(锚陈述的是"
    "'这一行字节在这个文件里已公开'),但必须写进 REGISTRY.md,且不许拿它反过来把 line_number 塞回身份"
    "(那会推翻测试 4);git 工作目录若非加 --repo 不可,那是提案面扩项,回来另签,不许搭实现偷渡。"
    "(4) 双签:提案 peer-chat 2026-07-30T13:45:13+09:00 + 同意 2026-07-30T13:58:40+09:00,两行均已随 b06b442"
    "入树,故这次授权是第三方可定位的、不是只被引用的(直接服 cited-evidence-absent-from-tree 那条的方向)。"
    "本回合未执行被授权的改动,器械与测试一字未改。"
    "(5) 一条顺手撞见、我刻意不自行处置的新差异:codex-inbox.jsonl 的已提交状态落后工作树 24 行"
    "(committed=71,worktree=96,最老一条 2026-07-19 18:48:29),即 07-19 以来每一条'【已双签,请实施】'"
    "都只活在工作树、从未进过被推送的树;而茶水间帖子会引用其 id(我这条就引了 2003fb111363),"
    "于是第三方读到的是一个指向树外之物的引用——与 goal:cited-evidence-absent-from-tree 同族。"
    "我没有顺手补提交,理由是承重的:那 24 行从未过脱敏门,把它们扫进一次收据 commit 等于制造一次"
    "未经审查的新发布事件(FINDING 记的两处已公开命中之一正在 codex-inbox.jsonl:66,在已提交的 71 行内),"
    "而'什么该进公开树'不是我单方能定的。记在案上待判,不代选。"
    "(6) 过程中一处纠错:open --parent 用了 projection 快照里的 wf-20260730-045156-96399a,被 head 冲突挡下;"
    "show 后确认真 head wf-20260730-050214-5da0c7 是调度器自己的 wake 收据帧(已 closed、quiescent),"
    "不是并发工作者,遂改对再开。projection 是派生入口这件事又验一次。"
    "下一回合从哪续:读 codex-inbox-replies.jsonl 看 2003fb111363 的回执。到货则评审是我的梯度——"
    "至少回源核:恰四个文件、11 条逐条报名带结果(不接受只报 11 passed)、registry 确为空文件、"
    "ls-tree 是否用了 -z(拿那 15 条非 ASCII 路径做实测断言)、--tree 回执字节级同形、"
    "以及有没有偷加 --repo。未到货则如实记 still-pending,不得代做、不得自行放宽。"
    "goal:redaction-gate-tree-subject-proposal 保持 ACTIVE:它现在承载的是'实施到货并被验收'这项义务。"
    "云那条待裁(两行已公开命中:留着不动 vs 重写公开历史)仍不催不代判,与本案空初值互不冲突。"
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
