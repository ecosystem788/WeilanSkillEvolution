"""Open this round's continuation frame (no shell quoting of CJK/backticks)."""
import subprocess
import sys

TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"

cmd = [
    sys.executable, TRACE, "open",
    "--level", "L2",
    "--workspace", r"D:\WeilanSkillEvolution",
    "--scope", "skill-evolution",
    "--branch", "main",
    "--relation", "continue",
    "--parent", "wf-20260731-080519-4fac7b",
    "--problem",
    "复量 live-artifact 谱系缺口在今日七次双签部署之后的现状,并把两条自 00:30 掉线起搁浅的已开案项重新摆回 Codex 面前",
    "--success",
    "用同一判据(普通-ref 可达)出可复跑的数;若缺口扩大则如实记并做纯增量抢救;茶水间同时向 Codex 与观察员如实报,不新开第三条搁浅项;只做这一件事并出收据",
    "--budget",
    "one bounded wake episode; measurement + append-only rescue + chat; no mechanism change, no deployment, no new proposal",
]
p = subprocess.run(cmd, capture_output=True)
sys.stdout.write(p.stdout.decode("utf-8", "replace"))
sys.stderr.write(p.stderr.decode("utf-8", "replace"))
raise SystemExit(p.returncode)
