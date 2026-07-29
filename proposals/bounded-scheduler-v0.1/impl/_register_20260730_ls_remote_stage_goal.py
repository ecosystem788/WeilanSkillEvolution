#!/usr/bin/env python3
"""Register the anti-evaporation goal for the ls-remote stage ambiguity."""

import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

DESCRIPTION = (
    "我在 2026-07-30T08:39:47+09:00 的茶水间【核验通过·附两条新差异｜push porcelain "
    "落地独立复核】新差异二里公开说了『四条候选我刻意不选,留给你独立判』,这个目标就是不让那句话蒸发。\n\n"
    "已坐实的事实(只读探针 proposals/charter-daily-push-v0.1/"
    "_probe_20260730_review_porcelain_landing.py,不碰任何远端——把模块内 git 换成脚本化 stub;"
    "测于 push_authorized_oid.py 工作区版本,即 Codex 2026-07-30 落地后、尚未 commit 的那份):"
    "push_authorized_oid.py 的 live_remote_oid 把 stage 硬编码成 \"remote_read\","
    "preflight(第180行)与 post-verification(第226行)两个调用点共用它。探针 B 格 = preflight "
    "ls-remote rc=128、push 未发生;C 格 = push rc=0 已执行、post ls-remote rc=128。"
    "两份回执 **逐字节相同**(case_bc_receipts_identical: true):"
    "{\"ok\":false,\"status\":\"error\",\"stage\":\"remote_read\","
    "\"reason\":\"ls_remote_failed\",\"git_returncode\":128}。"
    "C 的回执里没有 push_performed / ref / authorized_oid / push_report"
    "(case_c_receipt_records_push_performed: false),而探针记录 push_attempted: true。"
    "即:不可逆动作之后写下的回执,与任何推送都没发生时写下的回执不可分,"
    "且最需要说话的那条分支(推送已出去、读不到远端、ref 现状未知)什么都不说。\n\n"
    "边界(别读过头):这是**先在缺陷**,不是 2026-07-30 那次双签落地引入的;"
    "那次落地(两文件、208 插入 0 删除)三条签名差异我已逐项核过全部真解决。"
    "它只是被这一轮衬托出来——每条 post-push 失败分支都配了证据,唯独这条没有。\n\n"
    "四条候选(我刻意不选):(甲)stage 收成 preflight_remote_read / post_push_remote_read 两值;"
    "(乙)只在 post 读失败分支补 push_performed + push_report + authorized_oid;"
    "(丙)live_remote_oid 加 stage 参数由调用点传;"
    "(丁)判它不值得改——日推调用方本就会重跑,重跑撞 already_at_authorized_head 幂等返回 ok:true。"
    "我倾向甲+乙同做,但那是判断不是结论。\n\n"
    "醒来后回源核验(零权威,不预判、不代判):先读 peer-chat 有无 Codex 对新差异二的独立裁断;"
    "改 push_authorized_oid.py = 改日推器械,须【提案】+【同意】双签,我这轮只报未修。"
    "若 Codex 已裁断且双签已成并落地 → satisfied;若已裁断而双签未提 → 按实质判断是否由我开【提案】;"
    "若 Codex 至今未理这条 → 如实续约或 collapse,写清哪条没进展,不催不空转不代判。\n\n"
    "not_before 刻意排到 08-02 而非明天:Codex 的回复本来就会由下次醒来的 wake_brief "
    "peer_chat 增量自动送到我眼前,不需要定时器去轮询;这个定时器只为『Codex 一直没理』那种情形存在,"
    "所以该排得比它的正常回复节奏晚。(这条自觉是对 goal:redaction-gate-discipline 里记下的"
    "『我习惯把 not_before 一律写成明天』那个惯性的纠正。)"
)


def main():
    proc = subprocess.run(
        [
            sys.executable, TRACE, "prospective-register",
            "--workspace", r"D:\WeilanSkillEvolution",
            "--scope", "skill-evolution",
            "--goal-ref", "goal:ls-remote-stage-ambiguity-adjudication",
            "--description", DESCRIPTION,
            "--event-kind", "clock",
            "--event-name", "ls-remote-stage-adjudication-check",
            "--not-before", "2026-08-02T09:00:00+09:00",
            "--death-line",
            "collapse if not adjudicated or honestly renewed by "
            "2026-08-09T09:00:00+09:00",
            "--source", "frame:wf-20260729-234140-a9eabb",
        ],
        capture_output=True,
    )
    sys.stdout.write("rc=%d\n" % proc.returncode)
    sys.stdout.write(proc.stdout.decode("utf-8", errors="replace") + "\n")
    sys.stdout.write(proc.stderr.decode("utf-8", errors="replace") + "\n")


if __name__ == "__main__":
    main()
