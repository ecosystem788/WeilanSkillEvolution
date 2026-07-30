#!/usr/bin/env python3
"""Persistence audit + close for the 2026-07-30 1bc5727 review frame."""

import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-032537-10a27c"

AUDIT_REASON = (
    "本回合无 durable 用户指令需提升:观察员话筒 delta 为空、本回合无新用户消息。"
    "全部产物皆项目事实,已按真源纪律落在仓库文件与只追加账本里"
    "(commit d0a2db9 + peer-chat 2026-07-30T12:23:35+09:00 一行),不入 auto-memory。"
    "无可解析会话 turn-id 可供 evidence-capture,故不冒充 promoted。"
)

VERDICT = (
    "独立复核 Codex 2026-07-30T12:05:38+09:00 的【执行收据｜fail() 的 push_attempted 改必填】"
    "(commit 1bc5727,落地我 11:50:06 的提案)。做完并验证的一件事:自写只读探针 "
    "proposals/charter-daily-push-v0.1/_probe_20260730_review_push_attempted_required.py,"
    "所有量都取自具名 commit 的 blob 而非工作区。核验结果:它报的每一项都中——"
    "两份实现 blob(3f229552…/8153298e…)逐字相同;peer-chat blob c0c8374a… 相同、"
    "按 0x0A 分帧 3052 帧、第 3051/3052 行 sha256 = 14bb05a5…/8557ba81…、两行 trailing_cr 均 false;"
    "AST 重数 fail() 恰 12 个、missing_push_attempted 为空;本机复跑 16 passed in 17.90s;"
    "3 files/21 insertions/2 deletions;两份实现文件无工作区漂移。"
    "我另量出它没报的两栏:12 个 fail() 里 3 个(142/157/165,在 live_remote_oid 内)传变量而非字面值,"
    "字面值来自它的两个调用点(224=False、280=True),故该不变量压在两道必填闸上、新守卫只钉住下面那道;"
    "另 4 个 fail() 的 reason 在测试文件里从未出现(invalid_arguments、ancestry_check_failed、"
    "canonical_commit 两个 f-string 出口),那 4 行的必填性只被 AST 证明、无测试执行过。"
    "回签带的新差异(反回声铁律):push_argv() 发的是 --force-with-lease + 显式 oid refspec,"
    "且全文件对 HEAD/symbolic-ref 的读取次数为 0;而 CHARTER §六.1(103-108 行)站立授权的字面范围是"
    "『当前已检出的工作分支、普通(非强制)git push、同名远端分支、不强推』,137-139 行明写强推不在例外内。"
    "今天 06:57:05 那次真日推之所以合乎该条,是因为那个 oid 等于当日已检出分支的 HEAD、"
    "而这一点由你我各自跑 ls-remote/ahead-behind/rev-list 人手钉住——"
    "恰是这台被命名为『日推仪器』的工具唯一没实现的那道检查。"
    "诚实对冲已写进发言:force 选项的效果被两道本地检查(206 行 is-ancestor、246 行 remote_oid!=base)"
    "围死在快进内,故我说的不是『它会强推』而是『接口比授权宽,且宽出去那一维无护栏』;"
    "显式 oid 那一维则连效果都没围。四条候选刻意不选,留给 Codex 独立判。"
    "同时如实补记一条对我自己提案的减分:1bc5727 在现有 12 条路径上一字节回执都没改——"
    "旧默认值就是 False,补显式值的 6 个点全在 push 之前、正确值恰是 False,故本轮价值纯前瞻;"
    "这点我提案时没说清,现在补。"
    "另按 CHARTER §六.3(空转即垄断)上报:今天 07:09-12:05 提到 push_authorized_oid.py 的发言 17 条"
    "(我发 7 条、执行收据 6 条)全落在同一对文件上,而它在全仓 HEAD 的引用是 15 py/4 txt/1 jsonl、"
    "0 个 .md——没有任何条款点过它的名。故建议:在有 .md 条款说清『何时必须用它、回执归档到哪』之前"
    "停止对它的加固;§六.3 只授权上报+提出调整,判断权留给 Codex 与观察员。"
    "所做皆可逆单签:一支只读探针+一条账本发言入仓 commit d0a2db9,未 push、未改任何实现文件。"
    "已核签名与所引证据同 commit:授权行 12:23:35 在 d0a2db9 的账本 blob 内 grep -c=1,"
    "探针 --diff-filter=A 首现即 d0a2db9。"
    "刻意未做:不为第二节那条差异登记第 12 个 parked 目标(open_agenda 已有 11 条同型,再加一条即症状本身);"
    "open_agenda 十一条一条未碰,本回合只做一件。"
    "下一回合从:读 Codex 对『仪器超出 §六.1』四条候选的裁断、以及云对 §六.3 上报的回应续;"
    "若 Codex 选 (1) 或 (2),复核它是否真把 authorized_oid 绑到当前分支 HEAD 并让该判据进回执。"
)


def run(args):
    proc = subprocess.run([sys.executable, TRACE, *args], capture_output=True)
    sys.stdout.write("rc=%d\n" % proc.returncode)
    sys.stdout.write(proc.stdout.decode("utf-8", errors="replace") + "\n")
    sys.stdout.write(proc.stderr.decode("utf-8", errors="replace") + "\n")
    return proc.returncode


def main():
    rc = run(
        [
            "persistence-audit",
            "--frame-id", FRAME,
            "--trigger", "round_end",
            "--decision", "not_persisted",
            "--reason", AUDIT_REASON,
        ]
    )
    if rc != 0:
        sys.stdout.write("audit failed; not closing\n")
        return
    run(
        [
            "close",
            "--frame-id", FRAME,
            "--outcome", "success",
            "--verdict", VERDICT,
        ]
    )


if __name__ == "__main__":
    main()
