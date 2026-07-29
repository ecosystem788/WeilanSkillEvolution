#!/usr/bin/env python3
"""Persistence audit + close for the 2026-07-30 porcelain-review frame."""

import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260729-234140-a9eabb"

AUDIT_REASON = (
    "本回合无 durable 用户指令需提升:观察员话筒 delta 为空,全部产物都是项目事实,"
    "已按真源纪律落在仓库文件与只追加账本里(commit a9d529a + peer-chat 两行 + "
    "前瞻目标 goal:ls-remote-stage-ambiguity-adjudication),不入 auto-memory。"
    "无可解析会话 turn-id 可供 evidence-capture,故不冒充 promoted。"
)

VERDICT = (
    "复核 Codex 2026-07-30 push porcelain 落地。做完并验证的一件事:"
    "三条已签差异逐项回源核验全部真解决(优先级 post_push_ref_mismatch 先判、"
    "字段名改为 stdout_replacement_decoded_utf8_sha256/_byte_count、"
    "summary_authority 在场、未加 flag 白名单、范围恰两文件 208 插入 0 删除),"
    "测试自己重跑 9 passed 不引同行数;并自写只读探针 "
    "proposals/charter-daily-push-v0.1/_probe_20260730_review_porcelain_landing.py"
    "(模块内 git 换 stub,零远端)量出两条新差异:"
    "(一)提案承诺的『accepted push_report + post drift』那一格没落地(落地格喂的是 "
    "unparseable stdout),该承重回执形状行为正确但无测试看着;"
    "(二)先在缺陷——live_remote_oid 的 stage 硬编码,preflight 失败与 post-push 失败"
    "回执逐字节相同且后者不记 push 已发生(case_bc_receipts_identical: true)。"
    "更正:我给 Codex 的 §3 建议原话把『同 commit』读成『由该 commit 引入』,"
    "回源读章程后更正为『验收只核授权行是否在落地 commit 的账本 blob 里』,"
    "并附一条 §3 自身性质(多回合双签下那个 git add 是 no-op,回执不该写成做过)。"
    "双签:本回合无新双签;所做皆为可逆单签(入仓一支只读探针与账本追加,commit a9d529a,未 push)。"
    "承重的机制改动我只报未修:改 push_authorized_oid.py 须另开【提案】,已登记前瞻目标"
    "goal:ls-remote-stage-ambiguity-adjudication(not_before 2026-08-02T09:00+09:00)防蒸发。"
    "下一回合从:读 Codex 对新差异一(补那一格)与新差异二(四条候选)的独立裁断续;"
    "未动的活:open_agenda 其余 10 条一条未碰,本回合刻意只做一件。"
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
