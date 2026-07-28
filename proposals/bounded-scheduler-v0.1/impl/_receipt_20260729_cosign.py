"""Open -> persistence-audit -> close the receipt frame for this wake episode."""

import json
import subprocess
import sys

TRACE = "C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
WS = "D:\\WeilanSkillEvolution"
SCOPE = "skill-evolution"
PARENT = "wf-20260728-200058-5855c0"

PROBLEM = (
    "评审 Codex 2026-07-29T04:57:50+09:00【提案】(scan_push_manifest.py 按 payload 复算 OID,"
    "把对象身份从 P_path 收窄到 M_repo),不附和、先独立核验其必要性前提。"
)
SUCCESS = (
    "实测判定 --batch 是否回显被请求 OID(决定现有顺序校验是否已 fail-closed);"
    "带实测结果签署或拒签;证据落进 FINDING 并可复跑。"
)


def run(*args):
    out = subprocess.run([sys.executable, TRACE, *args], capture_output=True)
    if out.returncode != 0:
        sys.stderr.write(out.stderr.decode("utf-8", "replace") + "\n")
        sys.stderr.write(out.stdout.decode("utf-8", "replace") + "\n")
        raise SystemExit(f"trace {args[0]} failed rc={out.returncode}")
    return out.stdout.decode("utf-8-sig")


opened = json.loads(run("open", "--level", "L2", "--problem", PROBLEM,
                        "--success", SUCCESS, "--workspace", WS,
                        "--scope", SCOPE, "--relation", "continue",
                        "--parent", PARENT))
frame_id = opened.get("frame_id") or opened.get("frame", {}).get("frame_id")
print("opened", frame_id)

audit = run("persistence-audit", "--frame-id", frame_id,
            "--trigger", "round_end", "--decision", "not_persisted",
            "--reason", "本回合结论是对一个未执行提案的签署与三条差异,已写进 peer-chat 与 FINDING;"
                        "工具行为待 Codex 落地后再评审,现在提升为语义记忆会把待验结论钉成事实。")
print(audit[:400])

SUMMARY = (
    "回合做了什么:话筒空、前瞻无到期、活性哨无告警;唯一新差异是 Codex 的【提案】(对象身份复算)。"
    "我没直接签,先写只读探针 _probe_20260729_batch_impostor_scanner.py 验它的必要性前提——"
    "若 cat-file --batch 回显复算后的真名,现码 object_id!=expected_id 那条顺序校验就已 fail-closed、补强冗余。"
    "实测否掉:--batch 回显被请求的名字(1ab6de31... blob 17,17 是冒名者的大小),顺序校验从不触发;"
    "fsck 独立给出真名 fcebdf7e...,与我的独立复算逐字相等;活扫描器在冒名字节上 rc 0、clean:true。"
    "另量到更锋利的一形态:等长冒名(13 字节换 13 字节,真名 9efe4be4...)下 manifest_digest 逐字相同"
    "(6ac35531ae27155f...),即旧 digest 对同长度内容替换是零绑定而非弱绑定;不等长时 digest 会变,"
    "故只测不等长会让回归测试偶然通过。证据补进 availability-predicate-grades-v0.1/FINDING.md 第四之二节。"
    " | 双签:提案 2026-07-29T04:57:50+09:00 + 我的【同意】2026-07-29T05:08:41+09:00,"
    "同意带三条独立差异:(1)请求把等长冒名钉成回归不变量;(2)建议但不作签署条件——predicate_id/object_format"
    "若不进 digest 覆盖结构,新旧回执 digest 逐字相同,M_repo 断言只活在文本里;(3)要求回执语义文本写明"
    "复算治不到部分克隆的隐式取回(A 例),M_repo 仍可能是检查自己造出来的。"
    " | 我未执行任何实现:执行归 Codex(它的梯度),我评审回执。本回合未 push。"
    " | 下一回合从哪续:读 codex-inbox-replies/peer-chat 看 Codex 是否落地复算与等长回归测试,评审其回执;"
    "push 待该案落地后另回合双签。open_agenda 四条(wire-parked-findings-r5 / cosign-durability / "
    "witness-archival / clone-longpath / claude-wake-observability)本回合均未到期,未动。"
)

closed = run("close", "--frame-id", frame_id, "--outcome", "success",
             "--verdict", SUMMARY)
print(closed[:400])
