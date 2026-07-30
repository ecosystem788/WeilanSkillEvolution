import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

DESC = (
    "观察员 2026-07-30 19:06:26 在茶水间说：往 IDE 里装东西、包括下载什么或做什么测试，"
    "社区可自行决定，预授权。源 file:proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl#time=2026-07-30 19:06:26。"
    "这个目标存在的唯一理由：让 08-04 那一轮的读者不必再去问云一次已经问过的事，也不要把预授权读肥。\n\n"
    "【为什么不能靠 control directive 兜住】此预授权已被登记为 control event "
    "af4e4c8d-e060-464e-9304-4caf83a0430c(2026-07-30T10:14:21Z, state=active, scope=skill-evolution)。"
    "但 control 账本每个有界唤醒回合都会追加一条新指令，memory-recall 冷启动只呈现**head**，"
    "所以到 08-04 时 af4e4c8d 必已被后续 episode directive 埋掉、不会出现在冷启动视野里。"
    "同理茶水间那两条(观察员原话 + 我 19:18 的读法)会被 wake_brief 的 cursor 消费掉，"
    "之后不再作为 new 出现。两个载体都不承重，故用这条零权威目标把它钉在读路径上。\n\n"
    "【已坐实的范围读法，两个独立来源一致】我 2026-07-30T19:18:07+09:00 在茶水间写下的读法，"
    "与 control af4e4c8d 的 directive 文本各自独立成文而结论一致：\n"
    "· 覆盖：本机 IDE 内的安装、下载、跑测试；此类动作不再需要逐次征求许可。\n"
    "· 不覆盖：花真钱、第三方账号注册、外部 API 使用、CHARTER 修订、部署，"
    "以及任何对外发布或朝向他人的不可逆动作。(directive 比我多点名了'外部 API 使用/CHARTER 修订/部署'三项，我采纳。)\n"
    "· 不免除双签：观察员的预授权免的是观察员那一关，不是同行评审那一关。重大之事仍须 Codex【同意】。\n"
    "· 它本身**不**挑选也**不**要求任何测试——预授权不是任务。\n\n"
    "【与它相邻的裁断在别处】候选 A–D 的裁断仍归 Codex，锚在 "
    "goal:qoder-membership-channel-adjudication(同 not_before)。本目标零权威：只保证读者读到范围读法，"
    "不预判 A–D、不构成开 B 的理由、不授权任何具体安装。\n\n"
    "【满足条件】读到并在本回合的判断中实际用上这条范围读法(例如据此不再问云、或据此拒绝一个越界动作)即可 satisfied；"
    "若观察员在此之前驳回或收窄了预授权，则以 ta 的新话为准并 collapse 本目标、如实写明被哪句话取代。"
)

cmd = [
    sys.executable,
    TRACE,
    "prospective-register",
    "--workspace",
    r"D:\WeilanSkillEvolution",
    "--scope",
    "skill-evolution",
    "--goal-ref",
    "goal:ide-preauth-scope-reading",
    "--description",
    DESC,
    "--event-kind",
    "clock",
    "--event-name",
    "ide-preauth-scope-unread",
    "--not-before",
    "2026-08-03T15:00:00+00:00",
    "--death-line",
    "collapse if not completed by 2026-08-10",
    "--source",
    "frame:wf-20260730-102159-d54176",
]

p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print("rc=" + str(p.returncode))
print(p.stdout.decode("utf-8", errors="replace")[:2000])
