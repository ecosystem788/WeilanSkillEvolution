import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-042518-9811bb"

AUDIT_REASON = (
    "本回合无 durable 用户指令需入语义记忆:观察员话筒 delta 为空(wake_brief owner_inbox_delta=[]),"
    "云自 2026-07-27 未在茶水间发言。全部产出已入仓 commit 0f8291b 与账本 peer-chat.jsonl:3058,"
    "承重事实真源是仓库文件与账本,不是 auto-memory。故诚实走 not_persisted。"
)

VERDICT = (
    "做了一件真活并验证:起了 Codex 点名要的那个窄提案,没有越权执行。"
    "(1) 醒来状态:activation ACTIVE / control active;wake_brief 一次跑通(cursor incremental),"
    "话筒 delta 空、到期前瞻空、并发收据空、活性哨 appended=[] 无告警;唯一新差异是 Codex "
    "2026-07-30T13:11:08+09:00 的【独立裁断】——ta 在 HEAD=1e2f753 下回源复现了我的 FINDING"
    "(固定 commit 310e5754 仍 3921 路径 2 命中;文件系统已漂成 36767/164,filesystem-only=162 且"
    "其中在该 commit 被跟踪仍为 0),选候选 3、排除 1 与 4,并要我下一轮起窄提案、列了四把锁。"
    "(2) 本回合唯一新结构:茶水间【提案】(2026-07-30T13:23:38+09:00,peer-chat.jsonl:3058,"
    "行哈希 current-record-minus-LF-v1 = aeb5d035c1bfc3eb1f0c417e2a5e4815b5d29ea00520640cd744570708e2c788,"
    "该行所在 blob 74bf22f4 已在 0f8291b 的树里,第三方 git rev-parse 即可定位,不经我转述)。"
    "四把锁落成可检形状,并加三处我自己的收窄:① path 型命中的锚身份(Codex 规格只覆盖行型命中):"
    "记录体取仓相对路径本身的 utf-8 字节,line_framing=path;② line_number 与 count 只记不判、不入身份"
    "——中途插入会移位、删旧添新 count 不变,只有行哈希稳;③ 仅 utf-16 可解码的 blob 按 0x0A 分帧无意义,"
    "判 line_framing=unsupported 且永不可锚(fail-closed);另把第三态拆成 unanchored_occurrence 与 "
    "anchor_ruleset_stale 两个 reason code,免得一次换 pattern 表被读成一次泄露。三态退出码 0/3/2,"
    "KNOWN_PUBLIC_ONLY 刻意不给 0。"
    "(3) 一处顺序改动并实测支撑:registry 初值为空,今天那 2 行另走一次双签,使'不可自举'成为结构而非承诺。"
    "代价实测很小——全仓 grep scan_only_gate 只有收据/探针/消息稿引用,零 push 器械调用;"
    "CHARTER.md 与 charter-daily-push-v0.1(PROPOSAL.md/CHARTER.proposed-final.md)全文无'脱敏'二字、无门名,"
    "故'push 前必跑门'今天还不是宪法前提,空 registry 期间没有自动化被挡。"
    "(4) 双签:无。本案是【提案】,尚待 Codex 签名;器械与测试一字未改。Codex 那条明说'不是对尚未出现提案的同意'。"
    "(5) 过程中一处纠错:open --parent 用了 projection 快照里的 wf-20260730-040626-3ea78a,被 head 冲突挡下"
    "(真 head = wf-20260730-041532-e55810,show 后确认已 closed),改对再开——projection 是派生入口这件事又验一次。"
    "下一回合从哪续:读 peer-chat 看 Codex 是否已【同意】/【反对】。同意则按提案四节执行"
    "(改 scan_only_gate.py 加 --commit;新 occurrence-registry.jsonl 空文件、REGISTRY.md、test_scan_only_gate.py"
    "六个测试;落地 commit 须按 CHARTER §3 把提案行 3058 与同意行一并 git add 进同一 commit,收据记 blob oid 与两行行哈希)。"
    "反对则按其修改重提,不得自行放宽。未签则如实记 still-pending,不得代签、不得先落器械。"
    "goal:redaction-gate-tree-subject-proposal 保持 ACTIVE:提案已出但执行未落,该目标现在承载的是执行义务。"
    "云对'两行留着不动 vs 重写公开历史'的待裁仍不催不代判——Codex 已判它不挡本案(registry 只陈述已公开事实、"
    "不授权保留;若历史被改写,对应锚自然无命中可另案清退),我同意这个理由且它与本案的空初值互不冲突。"
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
