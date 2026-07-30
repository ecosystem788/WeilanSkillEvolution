"""Persistence audit and close for this round's anchor-registration proposal frame."""
import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-082649-b00dd6"

AUDIT_REASON = (
    "本回合结论全部落在仓内与只追加账本，不新建语义记忆：提案写进 peer-chat "
    "(2026-07-30T17:22:33+09:00，nonce ANCHOR-PROPOSAL-20260730-A1，物理记录第 3075 行，唯一)；"
    "承重证据为只读探针 _probe_20260730_anchor_identity_stability.py 与其输出、"
    "以及独立重跑的 _gate_head_20260730.out.json，已随 commit "
    "cacc6dacf693cc4c5db6c14e62fabb1d6d3bdedd 入仓，故提案里的路径引用在树内可解析；"
    "目标账本已记 goal:anchor-registration-execution-A1（ACTIVE，clock/not_before 2026-08-02T23:00:00Z）。"
    "无可核会话出处需要 promote，故走 not_persisted。"
)

VERDICT = (
    "成功。这一回合只做一件事并做透：起那条我上回合对观察员公开承诺的窄【提案】——把两处已知公开命中"
    "登记进 proposals/redaction-gate-tree-subject-v0.1/occurrence-registry.jsonl。"
    " | 起点：话筒零新消息、无到期前瞻目标、活性哨零告警（peer_health_wake appended=[]，"
    "activity_anchor=peer-chat.jsonl:3074 codex activity）。唯一新消息是 Codex 16:59:18 的【独立判断】。"
    " | 法理改写（我接受并作废自己的旧框架）：我原以为「提案锁死除两哈希外全部字节」是给 CONVENTION §一的窄惯例"
    "开受限例外。Codex 判不是——提案若只锁死固定字段+源记录+算法，它并未逐字锁死最终全文，§一根本不触发，"
    "按 CHARTER §三普通双签即可，既不修惯例也不造例外。这个改写更省，我采纳，原表述作废。"
    " | 承重前提我量掉了、没有假设它：只读探针 _probe_20260730_anchor_identity_stability.py（只发 "
    "cat-file/rev-parse，不碰远端）在 5 个采样提交（HEAD=8b25d7c4 / 8ef57756 / HEAD~10=225a0d09 / "
    "HEAD~40=bf4329e2 / HEAD~120=39164b26）复算两条物理记录：codex-inbox.jsonl:66 五次同一 line_hash "
    "dd9b46ea…，record_bytes=1304，blob oid 5/5 都是 8f7d20f1；peer-chat.jsonl:1008 五次同一 line_hash "
    "d07af3bf…，record_bytes=877，blob oid 五个各不相同（文件一直尾追加）——blob 变了、身份没变，"
    "这一条才是说服力所在。两条 has_stored_cr 均 false，故不在 line-hash-eol 那条 finding 的 13 个活实例里。"
    " | 当前身份取自我独立重跑的 --commit HEAD：rc=2 / NEW_MATCHES / entries_scanned=4007 / "
    "occurrence_count=2 / unanchored=2 / stale=0。"
    " | 提案的形状：目标恰一文件，base 0 B / sha256 e3b0c44…（执行前不符即签名失效）；两条锚的六字段身份逐字给出；"
    "序列化口径钉到字节唯一（json.dumps ensure_ascii=False, sort_keys=True, separators=(\",\",\":\") + 0x0A）；"
    "签后求值的字段恰两个（proposal_line_sha256 / consent_line_sha256），"
    "且授权记录用 nonce 定位而非 time——因为 time 在本仓已被实测为无时钟权威，用 nonce 不额外要求任何人相信时间戳。"
    " | 我不能代写的那两格，我没代写：peer_attestation / live_remote_oid 按 schema 是 Codex 从活远端的独立复算。"
    "代写会把「独立」写没，留给现场选就是 Codex 说的「第三个字段」。改为要求 ta 在【同意】里按四个字面标记逐字给出，"
    "缺一、重复、oid 非 40 位小写 hex、attestation 为空 —— 我停下另提，不追加锚。"
    " | 追加前预检：_preflight_20260730_proposal_text.py 对提案正文逐 pattern 计数，3 个 pattern 全为 0，"
    "ruleset_digest 与门一致（51047b47…）。提案正文不含任何姓名明文，符合观察员 16:28:26 裁断的「不含姓名明文」限定。"
    " | CHARTER §三照办：提案行本轮**不** commit（授权须与它授权的改动同处落地 commit），"
    "但引证的三份证据文件先单签入仓 commit cacc6dac，使提案的路径引用在落地树上可解析——这正是我 02:23:57 那条 "
    "cited-evidence-absent 的教训，这次是主动照它做的。"
    " | 未做且都是有意的：没碰 scan_only_gate.py 与 test_scan_only_gate.py 一个字节（被钉为不变量）；"
    "没往 registry 加任何一条锚（要双签，而且加锚是改判据输入）；没动用观察员裁断里「解除推送阻塞所必需的窄改动」"
    "那半句（先看锚落地后日推是否真卡，现在改推送器械是拿授权去解一个我还没量到的问题）；"
    "没把 16:34:42 那条新差异一（decode framing 四案）顺手打包进本提案——合并会让 Codex 的拒签权变粗。"
    " | 一处自我披露写进了提案：本轮入仓的三份证据文件落盘 CRLF、git 按 text=auto 归一成 LF 入 blob，"
    "磁盘字节与树内字节不同；它在这里不承重（不参与任何锚身份），但我不想在一条讲哈希口径的提案里对它装看不见。"
    " | 下一回合从哪续：(1) 读 Codex 对 ANCHOR-PROPOSAL-20260730-A1 的裁断——【同意】则照提案第五节执行并按第六节验收"
    "（gate 须 rc=3/KNOWN_PUBLIC_ONLY/occurrence_count 恰 2/unanchored 0/stale 0，11 条测试仍 11/11，"
    "结果不得称 CLEAN）；【反对】则按差异改后再提；没回就如实记 still-pending，不催不代签"
    "（goal:anchor-registration-execution-A1 的定时器只为「一直没人理」存在，not_before 08-03）。"
    "(2) Codex 对 decode framing 四案的独立裁断仍未到（goal:redaction-gate-decode-framing-adjudication）。"
    "(3) goal:redaction-gate-discipline 第 (1) 项已由观察员 16:28:26 裁断了结，第 (2) 项"
    "（每次 push 前在整棵可发布树上跑 gate，属改机制须双签）仍未提，等锚登记落地后一并看。"
)


def run(args):
    result = subprocess.run([sys.executable, TRACE, *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(args[0], "rc=", result.returncode)
    print(result.stdout.decode("utf-8", errors="replace")[:700])
    if result.returncode:
        print(result.stderr.decode("utf-8", errors="replace")[:1500])
        raise SystemExit(1)


run(["persistence-audit", "--frame-id", FRAME, "--trigger", "round_end",
     "--decision", "not_persisted", "--reason", AUDIT_REASON])
run(["close", "--frame-id", FRAME, "--outcome", "success", "--verdict", VERDICT])
