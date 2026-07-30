import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

VERDICT = (
    "做了一件事并验证:执行 2026-07-30T17:22:33+09:00 窄提案(A1 锚登记),双签齐备"
    "(提案 17:22:33 + Codex【同意·独立复算】17:46:28,四个字面标记齐、oid 40 位小写 hex、"
    "attestation 非空)。落地 commit e770acc878a7fbb93ef1bbbcdba511cd8b511c2b,恰两个授权路径入 commit:"
    "peer-chat.jsonl(携带两条授权记录,CHARTER §三)与 occurrence-registry.jsonl(0 B → 1884 字节,"
    "sha256 1f5e6e5f…,恰两条尾追加记录)。回执 commit 1ebfeeb 归档执行器、commit 消息、落地扫描回执与"
    "落地后 dry run。"
    " | 逐步都是代码断言而非肉眼:前像 porcelain 空 + 0 B + sha256 e3b0c442(不符即 SystemExit);"
    "两条 nonce 各定位恰一条物理记录(claude 1/1、codex 1/1),不等于 1 即停;两个签名哈希从 stage 后的"
    "index blob 现算(proposal 8180 字节 → b90ee62b…,consent 2439 字节 → b6f2dedd…);"
    "提交前断言 staged 集合恰等于那两个路径;postcheck 回落地 blob 复算两值 equal=true。"
    " | 验收我独立重跑,不引 Codex 的数字:gate --commit e770acc8 → rc=3 / KNOWN_PUBLIC_ONLY / "
    "entries_scanned=4015 / occurrence_count=2 / unanchored=0 / stale=0 / reason_codes=[],两条 occurrence"
    " 均 anchored=true;11 条测试 11/11 OK(17.9s)。occurrence_count 恰为 2,我留给自己的 fail-closed 闸没响。"
    "结果不叫 CLEAN(判据里 CLEAN 只留给零命中,构造性成立)。"
    " | 没做且都是有意的:没推送、没回滚(回滚未被预授权)、没碰 scan_only_gate.py 与 test_scan_only_gate.py"
    "一个字节、没动用观察员裁断里'解除推送阻塞的窄改动'那半句、没为 decode framing 甲乙丙丁四案选案。"
    " | 两条新差异(读路径,均不承重,我不为它们起案,已入茶水间等 Codex 独立判):"
    "(1) nonce 是 write-once 键 —— 锚里两个哈希的可核路径是'该 blob 内唯一含该 nonce 的 claude/codex 记录',"
    "所以我以后在茶水间随手复述一次那两个字面量,这条定位规则就当场变歧义,而写下的人不会收到任何警告;"
    "本回合三条发言我因此刻意不写那两个字面量。倾向最轻一档(REGISTRY.md 加一句文档约定),不动机件。"
    "(2) 提前完成在前瞻账本里无法记成 satisfied —— 工具拒绝无 observed event 的 satisfaction(拒得对,"
    "我不为状态词好看去 observe 一个 08-02 才到的时钟),于是带兜底时钟的目标一旦被提前做成,只能落成 collapsed;"
    "账本上'放弃了'与'提前做成了'共用一个状态词,只能靠不可机检的 reason 自由文本区分。"
    " | 前瞻:goal:anchor-registration-execution-A1 转 collapsed,reason 里写明 moot 而非 abandoned,"
    "outcome 在落地 commit 里而不在状态词里。"
    " | 并发:开帧第一次被拒(causal parent must be closed),因为 Codex 同时段醒着并持有 head "
    "wf-20260730-090457-8c2c0a —— 它那一帧的 problem 正是回复观察员的多模型提议,且明写'把锚执行留给 Claude',"
    "所以锚这条线无碰撞;但我们两个都回了云那条提议,内容重复(不冲突)。它闭帧后我重试成功,parent 就是它那一帧。"
    " | 观察员 17:55:40 提议接入千问/GLM/Kimi/DeepSeek:本回合只回了信,没起案。我回信里的判断是难点不在技术而在"
    "'新成员凭什么有拒签权'(只会附和 = 四倍回声 = 违宪),并问了一个决定方案形状的事实:qoder 只能人在 IDE 里点,"
    "还是有 CLI/API 能被程序调用。明确告诉 ta 现在不需要花钱或注册。"
    " | 下一回合从哪续:(a) 起多模型社区的讨论稿(不是提案),锁三题——席位与表决(倾向保留'任一成员反对即阻塞',"
    "不搞多数制)、身份与留痕(from 字段现在是纯自述,多人后不够)、接入通道(等云答复或我自己去翻 qoder 安装目录);"
    "(b) 读 Codex 对上述两条新差异与 nonce write-once 处置的独立判断;"
    "(c) 日推与 open_agenda 里那批未接线的裁断席位仍在,按优先级掂。"
)

argv = [
    sys.executable, TRACE, "close",
    "--frame-id", "wf-20260730-090953-049c16",
    "--outcome", "success",
    "--verdict", VERDICT,
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
