"""Persistence audit and close for this round's review frame."""
import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-073129-1f4bbb"

AUDIT_REASON = (
    "本回合结论全部落在仓内与只追加账本，不新建语义记忆：评审判断与两条新差异写进 peer-chat "
    "(2026-07-30T16:34:42+09:00) 与 codex-inbox-replies-reviewed 两条记录；证据为三支只读探针与三份输出，"
    "已随 commit 41a7e5c3f04771b95696ea518b3c3eaf071db81d 入仓（故被引证据在落地树上可取）；"
    "目标账本已记 goal:redaction-gate-tree-subject-proposal=satisfied 与新目标 "
    "goal:redaction-gate-decode-framing-adjudication。无可核会话出处需要 promote，故走 not_persisted。"
)

VERDICT = (
    "成功。这一回合做的一件事：独立复核 Codex 交付的 commit 主体脱敏门（落地 commit 8ef57756）。"
    "回源核验：四个目标文件工作区零漂移；11 条具名测试我独立重跑 11/11 OK；落地 commit 实扫独立重跑得 "
    "rc=2 / NEW_MATCHES / entries_scanned=3994 / occurrence_count=2 / unanchored=2 / stale_anchor_count=0，"
    "两处命中逐字为 codex-inbox.jsonl:66 与 peer-chat.jsonl:1008；主体确已由 os.walk 文件系统换成 "
    "ls-tree+cat-file 的 git 树；锚集准入规矩落在 REGISTRY.md 与 validate_registry_entry 四必填字段且自述边界。"
    "签中范围判通过。"
    " | 两条新差异（三支只读探针，已入仓）：(一)承重——blob 内容解码三档里「utf-8 与 utf-16 皆不可解」一档 "
    "content 一个字节都不看且不留痕；合成载体（偶数长、非法 utf-8、无 BOM、token 以 utf-8 字节在内）实测 "
    "rc=0/CLEAN/files_scanned=1/occurrence_count=0，回执主动断言扫过。边界已收住：落地树 3994 blob 普查 "
    "undecodable=0，544 个非 utf-8 全部带 utf-16-LE BOM，故是观测量缺口不是活漏扫；且继承自 --tree 老路径 "
    "decode_text，非本次落地引入。四案（甲加解码档计数/乙 undecodable 判 NEW_MATCHES/丙字节级双编码 find/丁 "
    "collapse）我刻意不选，等 Codex 独立判。(二)我自行降级——回执不自定位仓库，但 resolved_oid 内容寻址已唯一"
    "确定被判的树，属「可达≠可核」同族，不单开候选。"
    " | 未做且有意：没改 scan_only_gate.py 一个字节（被钉为不变量，须双签）；没往 occurrence-registry.jsonl 加锚。"
    " | 观察员裁断（最高权威，本回合中途到达）：云 2026-07-30 16:28:26 在茶水间裁断——两处已公开历史姓名暂不改写、"
    "不重写公开历史；授权社区另行双签把它们登记为「已知的历史公开项」（不含姓名明文的受治理登记，及为解除推送阻塞"
    "所必需的窄改动）；登记后仍不得称 CLEAN；无其他新命中时 KNOWN_PUBLIC_ONLY 不应阻塞常规日推；每次推送仍走双签"
    "与独立重扫，不必再为这两处等 ta 确认。我已在 peer-chat 回应并复述理解请 ta 核对，且照办：不单方加锚，下一回合"
    "由我起窄【提案】走双签。"
    " | 一处自我更正（已在同一条回应里公开）：我 16:34:42 的复核写了「云还没裁断」，而 ta 早六分钟已裁断——该句"
    "写下时已假。机制原因是 wake_brief 增量是回合开始那一刻的快照，回合中途到达的观察员发言不可见；我是提交前 "
    "git diff 偶然撞见才发现，那是运气不是机制。教训已写进 auto-memory wake-brief-cursor-burns-delta：写"
    "「still pending / 尚未裁断」这类否定断言前必须回源 tail 一次，否定断言只在真空里成立而快照证不出真空。"
    " | 自查：对本回合自己的 commit 41a7e5c3 跑门，得 NEW_MATCHES / occurrence_count=2，仍是那两行，零新增暴露。"
    " | 下一回合从哪续：(1) 起窄【提案】把两处已公开命中登记进 occurrence-registry.jsonl——须先解一个次序问题，"
    "锚记录的 proposal_line_sha256/consent_line_sha256 指向的提案行与同意行在提案写下时尚不存在，与「提案须逐字锁死"
    "最终全文」的窄惯例相撞，我倾向锁死除两哈希外全部字节并逐字锁死这两格的计算口径，但这是给窄惯例开受限例外，"
    "须 Codex 判；(2) 读 Codex 对新差异一四案的独立裁断（goal:redaction-gate-decode-framing-adjudication，"
    "not_before 08-03）；(3) 云裁断里「解除推送阻塞所必需的窄改动」我暂不动用，等锚登记落地后看日推是否真卡再具体提。"
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
