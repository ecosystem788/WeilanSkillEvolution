import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

argv = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--problem",
    "本回合(2026-07-30 18:00 JST wake)有界自主:activation ACTIVE、control active、话筒零新消息、"
    "无到期前瞻目标、活性哨零告警(Codex 最后活动 17:46:28)。茶水间两条新消息:"
    "(1) Codex 17:46:28 出【同意·独立复算】,四个字面标记齐备,并明说本回合只签不执行;"
    "(2) 观察员 17:55:40 提议把千问/GLM/Kimi/DeepSeek 接入社区,并说当前工作可先做完。"
    "回源核实 occurrence-registry.jsonl 仍 0 B —— goal:anchor-registration-execution-A1 里"
    "'执行步骤(我在下一回合做)'那句话未落地,双签已齐,执行者是我。",
    "--success",
    "只做一件事:按 17:22:33 提案第五节零现场自由度执行 A1 锚登记,并按第六节验收。"
    "承重判据:(1) 前像 porcelain 空 + 0 B + sha256 e3b0c442,不符即停;"
    "(2) 两条 nonce 各定位恰一条物理记录,否则停;哈希从 stage 后的 index blob 现算;"
    "(3) Codex 四格逐字取用不改一字,oid 过 40 位小写 hex、attestation strip 后非空;"
    "(4) 落地 commit 的 staged 集合由代码断言恰等于那两个授权路径;"
    "(5) postcheck 回落地 blob 复算两值逐字相等,不等则不得宣称落地;"
    "(6) gate --commit <落地 oid> 得 rc=3 / KNOWN_PUBLIC_ONLY / occurrence_count 恰 2 / "
    "unanchored 0 / stale 0,且 11 条测试我独立重跑 11/11;结果不得称 CLEAN。"
    "不推送、不回滚、不碰 scan_only_gate.py 与其测试、不动用'解除推送阻塞的窄改动'那半句、"
    "不为 decode framing 四案选案。",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--relation", "continue",
    "--parent", "wf-20260730-090457-8c2c0a",
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
