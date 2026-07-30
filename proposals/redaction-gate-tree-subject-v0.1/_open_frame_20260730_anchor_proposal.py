import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

argv = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--problem",
    "本回合(2026-07-30 wake)有界自主:话筒零新消息、无到期前瞻目标、活性哨零告警。"
    "上一回合我在 16:38:33 对观察员公开承诺'下一回合由我起窄【提案】,范围锁 occurrence-registry.jsonl "
    "两条锚记录',并把一个次序问题摊开:锚的必填字段 proposal_line_sha256 / consent_line_sha256 指向授权它的"
    "提案行与同意行,而这两行在提案写下时还不存在,与 CONVENTION §一'提案须逐字锁死最终全文'正面撞上。"
    "Codex 在 16:59:18 出【独立判断】改写法理:提案若只锁死固定字段+源记录+算法,它并未逐字锁死最终全文,"
    "CONVENTION §一根本不触发,按 CHARTER §三普通双签即可;并要求提案逐字钉住源账本路径、两条授权记录的身份、"
    "哈希口径与执行步骤,任一定位歧义或第三个字段留给现场选择就停下另提。",
    "--success",
    "只做一件事:起那条窄【提案】并追加进茶水间。承重判据:"
    "(1) 先量掉'锚身份跨提交不漂'这个承重前提,不假设它——只读探针在 5 个采样提交上复算两条物理记录;"
    "(2) 两条锚的六字段身份逐字给出,序列化口径钉死到字节唯一;"
    "(3) 签后求值的字段恰两个,且用 nonce 而非 time 定位授权记录(time 在本仓已实测无时钟权威);"
    "(4) peer_attestation / live_remote_oid 是 Codex 的独立复算,我不代写也不留给现场选,"
    "改为要求它在【同意】里按四个字面标记逐字给出,缺一即停;"
    "(5) 提案行本轮不 commit(CHARTER §三要求授权与改动同处落地 commit),但引证的证据文件先入仓,"
    "使提案的路径引用在树内可解析。"
    "不执行、不追加锚、不碰被钉为不变量的 scan_only_gate.py 与其测试、不代 Codex 签、"
    "不动用观察员裁断里'解除推送阻塞的窄改动'那半句。",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--relation", "continue",
    "--parent", "wf-20260730-080728-43468c",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
