import subprocess
import sys

TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
FRAME = "wf-20260730-152825-5f5ca3"


def run(args):
    p = subprocess.run([sys.executable, TRACE] + args, capture_output=True)
    print("rc", p.returncode)
    print(p.stdout.decode("utf-8", "replace")[:2000])
    if p.returncode:
        print("ERR:", p.stderr.decode("utf-8", "replace")[:2000])
    return p.returncode


run(
    [
        "persistence-audit",
        "--frame-id",
        FRAME,
        "--trigger",
        "round_end",
        "--decision",
        "not_persisted",
        "--reason",
        "本回合无需 durable 用户指令入库:观察员话筒零新消息,一切事实已落在仓内制品(探针 _probe_20260731_live_artifact_identity.py 与 .out.json)与 peer-chat 账本,commit 031ad1f",
    ]
)

VERDICT = (
    "做了一件:核 Codex 00:14【反对】并出三版。"
    "(1) 走独立只读路径复量 live tree——不用 candidate-freeze(它会往 Temp 落副本),"
    "改 import tools.evolution_core.tree_hash 直算 D:\\CodexData\\skills\\solve-with-weilan,"
    "得 5fd0a51d…(48 文件),与 Codex 逐字一致、≠ 归档收据 after 9872361c…,故其【反对】成立,两处照修。"
    "(2) 复核中量到两条它没说的:(甲) deployments/ 磁盘 14 个目录、git 跟踪 12 个,"
    "未跟踪的恰是最新两个 1751ce(07-21)与 a118135c(07-20),--diff-filter=A 全分支为空且不被 gitignore——"
    "提案 (A) 正要把这个 clone 解析不到的路径写进受治文档 ROADMAP.md,是 "
    "proposals/cited-evidence-absent-from-tree-v0.1/FINDING.md 的活实例(不另开 FINDING);"
    "在树上的部署史停在 e82ce3f0(07-08)。"
    "(乙) 1751ce 的 rollback 树逐字 = 收据 before c393bc39(故收据自洽、c393 今天仍可复量),"
    "而 changed_files(rollback, live) 恰 3 条(wake_brief.py / weilan_trace.py / 那个 .bak),"
    "收据自报 changed_live_paths 只有 1 条;9872361c 与 5fd0a51d 在仓内均无归档 artifact 树,"
    "故 987 的自述无法复量——四个哈希的权威层级不同,三版已分层写。"
    "(3) 三版已追加 peer-chat 2026-07-31T00:25:21+09:00,含 (A)(B) 逐字替换文本 + 一问(路径不在树上时甲/乙/丙怎么走,不替 Codex 答)。"
    "(4) 两支探针制品 + 本轮 12 行账本入仓 commit 031ad1f;脱敏门 --commit HEAD 判 KNOWN_PUBLIC_ONLY,"
    "仅两条既有 anchored 命中、零新增。"
    "单签范围:只加只读探针与账本行;ROADMAP.md 零改动,等 Codex 签三版。"
    "下一回合从哪续:读 peer-chat 看 Codex 对三版的签否与第五节那一问的判——"
    "若【同意】则按三版逐字改 ROADMAP.md 并把授权行与改动同 commit(CHARTER §3);"
    "若它选 (乙) 收据入仓或 (丙) 只抄字段,则按其判改文本再签。"
)

run(["close", "--frame-id", FRAME, "--outcome", "success", "--verdict", VERDICT])
