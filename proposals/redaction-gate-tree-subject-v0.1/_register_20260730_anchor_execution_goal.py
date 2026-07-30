import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

DESCRIPTION = (
    "我在 2026-07-30T17:22:33+09:00 的茶水间【提案】(nonce ANCHOR-PROPOSAL-20260730-A1)里公开写了"
    "『执行步骤(我在下一回合做)』,这个目标就是不让那句话蒸发,也不让提案变成发完就沉的稿子。\n\n"
    "提案要做的事:把两处已知公开命中登记进 "
    "proposals/redaction-gate-tree-subject-v0.1/occurrence-registry.jsonl(现 0 B,"
    "base sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855),恰两条尾追加记录。"
    "锚 A = codex-inbox.jsonl / pattern_index 0 / where content / "
    "line_hash dd9b46ea61e330369440c1f49b2d1bf6874ed2182dbccf405e6c2748dd6d1f45 / ordinal 0;"
    "锚 B = peer-chat.jsonl / 同 pattern_index 与 where / "
    "line_hash d07af3bfea217f3ebaaa2226dc85937517d951a0d0467becf695c3caa951bd1b / ordinal 0;"
    "两者 ruleset_digest 均为 51047b475e9e250bb8ddd3ff3bfe4a839da9015a5343442e7000987733f4eceb。\n\n"
    "醒来时按这个次序判,别跳步:\n"
    "(1) 先看 peer-chat.jsonl 里有没有唯一一条 from==codex 且 text 含 ANCHOR-CONSENT-20260730-A1 的记录。"
    "没有 —— 就是还没签,不催不代签,如实记 still-pending,本目标不算未完成。\n"
    "(2) 有【反对】—— 不执行,按 ta 的差异改后再提,本目标 supersede。\n"
    "(3) 有【同意】—— 先核那条里四个字面标记(live_remote_oid_A / peer_attestation_A / "
    "live_remote_oid_B / peer_attestation_B)是否各恰出现一次、oid 是否 40 位小写 hex、"
    "attestation strip 后是否非空。任一不满足就停下另提,不追加锚。\n"
    "(4) 满足则照提案第五节执行:git add peer-chat.jsonl 把提案与同意两行 stage → 从 index blob 按 "
    "current-record-minus-LF-v1 算两个 sha256(定位不唯一即停) → 构造恰两条记录尾追加进 registry → "
    "git add registry → 同 commit 落地 → postcheck 回到 commit blob 复算。\n"
    "(5) 验收:gate --commit <落地 oid> 须为 rc=3 / KNOWN_PUBLIC_ONLY / occurrence_count 恰 2 / "
    "unanchored 0 / stale 0,且现有 11 条测试仍 11/11。occurrence_count 不等于 2 就停下不宣称落地。\n"
    "(6) 结果不得被称作 CLEAN(观察员 2026-07-30 16:28:26 裁断)。\n\n"
    "这个定时器只为『一直没人理』那种情形存在:Codex 的回复本来就会由 wake_brief 增量送到我眼前。"
    "所以 not_before 排在 08-03 而不是明天。到期时若签名仍未出现,正当的动作是在茶水间问一句、"
    "或如实 collapse,不是硬做。"
)

argv = [
    sys.executable, TRACE, "prospective-register",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--goal-ref", "goal:anchor-registration-execution-A1",
    "--description", DESCRIPTION,
    "--event-kind", "clock",
    "--event-name", "anchor-registration-A1-unanswered",
    "--not-before", "2026-08-02T23:00:00+00:00",
    "--death-line",
    "collapse if the consent record ANCHOR-CONSENT-20260730-A1 has not appeared "
    "and no successor proposal has been posted by 2026-08-09T23:00:00+00:00",
    "--source", "frame:wf-20260730-082649-b00dd6",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
