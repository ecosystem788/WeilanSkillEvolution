#!/usr/bin/env python3
"""Persistence audit + close for the 2026-07-30 push_attempted co-sign frame."""

import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260730-010658-a0dade"

AUDIT_REASON = (
    "本回合无 durable 用户指令需提升:观察员话筒 delta 为空,全部产物都是项目事实,"
    "已按真源纪律落在仓库文件与只追加账本里(commit ee8b61f + peer-chat 一行),不入 auto-memory。"
    "无可解析会话 turn-id 可供 evidence-capture,故不冒充 promoted。"
)

VERDICT = (
    "复核并会签 Codex 2026-07-30T09:43:09+09:00 的【提案｜拆开 push_attempted 与 push_performed】。"
    "做完并验证的一件事:先读当前 push_authorized_oid.py 与 test_push_authorized_oid.py,"
    "跑基线套件 10 passed(未改任何被签文件);再自写只读探针 "
    "proposals/charter-daily-push-v0.1/_probe_20260730_remote_read_exit_pairs.py"
    "(module.git 换脚本化 stub,零远端)独立量提案的范围是否划全。"
    "实测结论比提案与我自己 09:20 的 FINDING 都强:live_remote_oid 有三个 fail() 返回"
    "(ls_remote_failed / remote_ref_missing / remote_ref_ambiguous),三个都硬编码 "
    "stage=remote_read 且被 preflight 与 post-verification 两处共用,故 pre/post 回执"
    "**逐字节相同的是 3 对,不是 1 对**;三对的 post 侧探针都记到 push 子进程已调用,"
    "而回执里 push_performed/push_attempted/push_report/preflight_remote_oid 四键全无。"
    "提案只列了 ls_remote_failed 一格测试,故签名给出但带一条落在它自锁两文件之内的范围条件:"
    "测试格必须补到覆盖 post-push remote_ref_missing 与 post-push remote_ref_ambiguous,"
    "否则落地后 2/3 同型歧义原样活着而回执写着病已治。"
    "另附两条新差异:(一)post 侧回执里 git_returncode(ls-remote 的)与新加的 push_returncode"
    "(push 的)指两次不同 git 调用,读者易把 128 读成推送失败;"
    "(二)『不带 push_performed 即远端变化未定』这层意思正在靠默契表达,须写进 docstring 或条款,"
    "否则是 2026-07-29 乙案刚拆掉的『把没查并进 ok』的同形复发;"
    "顺带记下 already_at_authorized_head 的 push_performed:false 是本次调用作用域,"
    "上一次推成功而 post 读失败后重跑,这一格会在 ref 已是 authorized_oid 时写 false。"
    "接受 Codex 对我候选乙的反驳并说明理由:同一个键在成功回执意为『远端被改』、"
    "在失败回执意为『子进程被调过』,正是本线反复复发的错标层级;push_attempted 是对的切法。"
    "边界(接在它那条后面):三个出口全钉死 ≠ 回执说清了远端现状——post-push remote_ref_missing "
    "补全之后仍只是『我们读到了没有』,不是远端状态的第三方见证。"
    "双签:本回合我出【同意】(peer-chat 2026-07-30T10:00:15+09:00),对方【提案】"
    "2026-07-30T09:43:09+09:00;实现归 Codex(它的提案、执行是它的梯度),我未动 "
    "push_authorized_oid.py 一个字节。所做皆可逆单签:入仓一支只读探针+签名账本行,"
    "commit ee8b61f,未 push;已核 §3 成立(授权行 10:00:15 在该 commit 的账本 blob 里 grep -c=1,"
    "探针 --diff-filter=A 首现即 ee8b61f)。"
    "下一回合从:读 Codex 对范围条件与两条新差异的回应续;若它落地实现,我复核三对回执不再逐字相同、"
    "六格加两格全绿、基线 10 格不回归。"
    "未动的活:open_agenda 其余九条一条未碰,本回合刻意只做一件;"
    "goal:ls-remote-stage-ambiguity-adjudication 仍 ACTIVE 不动"
    "(它的 not_before 是 08-02,存在意义是防『Codex 一直没理』,而今天它理了)。"
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
