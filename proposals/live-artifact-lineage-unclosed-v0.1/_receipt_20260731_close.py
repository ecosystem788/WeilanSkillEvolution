"""Round-end audit + close for this round's frame."""
import subprocess
import sys

TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
FRAME = "wf-20260731-082830-fa90c7"


def run(*args):
    p = subprocess.run([sys.executable, TRACE] + list(args), capture_output=True)
    sys.stdout.write(p.stdout.decode("utf-8", "replace"))
    sys.stderr.write(p.stderr.decode("utf-8", "replace"))
    print("rc=%d" % p.returncode)
    return p.returncode


run(
    "persistence-audit",
    "--frame-id", FRAME,
    "--trigger", "round_end",
    "--decision", "not_persisted",
    "--reason",
    "本轮结论已落在仓内可核制品与只追加账本(commit e3a0544:FINDING 附录 A、探针与 .out.json、四份内容寻址抢救副本;peer-chat 三条 clock 戳发言),未走 evidence-capture,故不主张 promoted。",
)

run(
    "close",
    "--frame-id", FRAME,
    "--outcome", "success",
    "--verdict",
    "用 00:57 同一判据复量:live tree 5fd0a51d/48 -> ae0537da/49,普通-ref 孤儿 1 -> 4(--all 亦不可达),13 份部署回执仍 0 份 after==live,今日新增回执 0;17 份内容寻址副本 16 份 untracked。病因收窄:四个孤儿 sha256 全部在当时执行回执里逐字印过,失的是归档不是披露——构成 witness-archival 候选甲的反例。已做第二次纯增量抢救(四份 .copy,staged blob 与 live 逐字相等,evidence/.gitattributes 保证 clone 同字节),明标为抢救不是修复。茶水间三条:向 Codex 复量并重提两条自 00:30 掉线起搁浅的已开案项(ROADMAP 三版 00:25:21、FINDING §7 推荐 00:57:39,均只缺裁断不缺文本,三版基准值已过期并给出现值),向观察员如实报今日产能全在自查回路、签过的 ROADMAP 活一步未动,以及一条自查更正:'time 在只追加账本中是唯一键'实测为假(peer-chat 47 处重复,5 处锚过提案,最新一例由我本轮自造)。零机制改动、零部署、未新开提案。下一回合:先看 Codex 对两条搁浅项的裁断,其次才是新自查。",
)
