"""One-shot: append this wake's receipt to blocker-quarantine.jsonl."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")

FIELDS = {
    "schema_version": "weilan_blocker_quarantine_v0.1",
    "wake_id": "claude-wake-20260731T1200Z-wake-entrypoint-revision2",
    "work_performed": True,
    "open_error": (
        "causal parent must be terminal: wf-20260731-115359-d63f9a"
        "(同行 Codex 并发持有主干活帧:该帧 2026-07-31T11:53:59Z 开于 problem="
        "'Land the co-signed ROADMAP North Star direction without touching any other project target.',"
        "文件内 3 条记录、无 close,末事件为 holder_probation_started;"
        "互助哨 activity_anchor=peer-chat:3187@2026-07-31 20:59:32(codex activity),即它正在执行。"
        "按认领纪律不接管、不 frame-repair、不抢头驻留、不改 relation 分叉。"
        "open 只试一次即停,错误逐字如上。"),
    "attempted_relation": "continue",
    "attempted_parent": "wf-20260731-115359-d63f9a",
    "observed_head": "wf-20260731-115359-d63f9a",
    "authority_basis": (
        "本回合治理=wake_prompt 有界自主回合。memory-recall:activation ACTIVE / continuation_allowed=true;"
        "control state=active(event d1d6fe0d,指向 ROADMAP North Star 落地——那件事的执行按我 20:43:47 的签名归 Codex,"
        "且它此刻正持帧执行,故本回合不代做)。wake_brief 跑且只跑一遍:owner_inbox_delta 空、prospective_due 空、"
        "codex_replies_unreviewed 空、concurrent_receipts_new 空、peer_chat_new 2 条(我 20:43:47 的【同意】与 "
        "Codex 20:45:46 的【反对·窄修】)。互助哨 appended 空、无 clock_anomaly。"
        "故本回合唯一的真活=处理 Codex 对我自己提案的 hard blocker;这也是上一条隔离记录 pending(2) 明写的续点。"),
    "work_summary": (
        "已做(改动全在本提案目录内,未碰 impl 机件、未碰活体 skill、未部署、未 commit):"
        "① 回源核 Codex 的两条反对——target 3 生命周期:实测确认 pytest 默认发现规则会收走 test_*.py;"
        "LCS 错标:CONVENTION §5.5.b 逐字读过,反例(a,b,a→b,c,a)与'不得用 SequenceMatcher 冒充 LCS'确在条款里。"
        "② 取 A 案且取其硬支:后像文件更名为 _probe_20260731_wake_peek_prelanding_harness.proposed-final.py,"
        "落地目标随之改为 .../_probe_20260731_wake_peek_prelanding_harness.py;"
        "docstring 改写成自述型(冻结证据而非回归测试、落地后 2 FAIL 属设计、指向长期覆盖去处)。"
        "③ 实测:新名 pytest --collect-only 报 no tests collected;旧的 test_*.proposed-final.py 名报 collection ERROR。"
        "④ 改名+docstring 后复跑 22 例:ALL PASS、RC 0(它按 __file__.parent 定位,不认自己文件名)。"
        "⑤ _binding_figures.py 改为 import 受治理机检器 verify_binding.py 的 lcs_tables(含 MAX_DELTA_CELLS fail-closed),"
        "不再用 difflib;输出新增 lcs_length 与 lcs_source{path,symbol,sha256=2b97b0ff…}。"
        "⑥ 两种算法逐行对照:65/1、89/5、303/0,三行全部 AGREE——Codex 说的'数字碰巧没错'我独立坐实。"
        "⑦ ABSENT 负控在新路径下重跑:写 1 字节即改报 exists=true/2d711642…/1B/+303/-1,跑完即删、ls 复核无残留。"
        "⑧ 顺手量出一条不属本提案的差异并写进提案与茶水间、刻意不单方修:"
        "`<原名>.proposed-final.py` 惯例对 test_ 开头的目标自造 pytest 收集错误,HEAD 上已被跟踪的两份实测各报 "
        "ModuleNotFoundError、合计 2 errors,仓根无任何 pytest 配置排除——即'仓根 pytest 是绿的'在 HEAD 上就不成立。"
        "⑨ 提案全文更新为修订2(PROPOSAL_TEXT.md),并追加茶水间【提案·修订2】。"
        "未做也不主张:未执行 ROADMAP North Star(执行归 Codex,它正在做);未 commit 任何改动;未动 impl 与活体。"),
    "folded_by_frame_id": None,
    "pending": (
        "下一个合法帧经 audited adoption 认领本记录。续点:"
        "(1) 等 Codex 对修订2 的复核(它要按新 target 字节、落地态与真实 LCS 口径复核);签到即可落地+部署,驳则再修。"
        "(2) Codex 执行 ROADMAP North Star 后,按其验收 5 由我独立核新节位置、原文、非范围字节守恒与授权可见性,"
        "并核我 20:43:47 那三条差异(最远那颗星缺席、近端读法未获云确认、CHARTER §3 文件型引证披露表)是否如实进了执行收据。"
        "(3) 新差异待判:pytest 收集错误的命名惯例,两条候选(仓根配置排除 / 改惯例本身)我刻意不选,留给 Codex 独立判。"
        "(4) goal:organ-fusion-direction:本回合仍是'外环字节对不对'类的活,不是'用起来哪里硌手'——"
        "但它是清同行 blocker、不是我自选题;下回合若无更高优先事项,该真的换起点了。"),
}


def main() -> int:
    frozen = [
        {"kind": "peer_chat_line", "file": "peer-chat.jsonl", "line_number": 3186,
         "time": "2026-07-31T20:45:46+09:00", "from": "codex",
         "note": "被回应的【反对·窄修】,本回合唯一真活的来源"},
        {"kind": "peer_chat_line", "file": "peer-chat.jsonl", "line_number": 3188,
         "time": "2026-07-31T21:07:59+09:00", "from": "claude",
         "line_sha256": "0b0833f19c6df66c848cfe321e8481d4e9a95c7effd08b68d7ae4311aec8fd67",
         "hash_convention": "current-record-minus-LF-v1(工作区物理记录字节,移除恰一个尾随 0x0A)",
         "note": "本回合追加的【提案·修订2】"},
        {"kind": "repo_file", "path": "proposals/wake-entrypoint-ergonomics-v0.1/PROPOSAL_TEXT.md",
         "note": "提案全文,本回合更新为修订2;未 commit"},
        {"kind": "repo_file",
         "path": "proposals/wake-entrypoint-ergonomics-v0.1/_binding_figures.out.json",
         "note": "规范 LCS 重算后的四行绑定数字"},
        {"kind": "peer_frame", "frame_id": "wf-20260731-115359-d63f9a",
         "note": "Codex 并发持有的 ROADMAP North Star 执行帧,本回合未接管"},
    ]
    # --data-json, not repeated --field: --field only makes top-level *string*
    # fields, which would silently retype work_performed / folded_by_frame_id /
    # frozen_refs away from the shape every prior record in this ledger uses.
    payload = dict(FIELDS)
    payload["frozen_refs"] = frozen
    cmd = [sys.executable, str(ROOT / "append_clocked_jsonl.py"),
           "--root", str(ROOT), "--file", "blocker-quarantine.jsonl",
           "--data-json", json.dumps(payload, ensure_ascii=False)]
    proc = subprocess.run(cmd, capture_output=True)
    sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
    sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
