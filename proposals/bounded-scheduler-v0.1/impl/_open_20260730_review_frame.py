#!/usr/bin/env python3
"""Open this wake episode's receipt frame (relation=continue)."""

import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

PROBLEM = (
    "独立复核 Codex 2026-07-30 落地的 push porcelain 有界结构证据"
    "(push_authorized_oid.py + 其测试),判三条已签差异是否真解决,"
    "并如实报出复核中新量到的差异。"
)
SUCCESS = (
    "三条签名差异逐项回源核验;测试自己重跑;承重结论由自跑只读探针支撑而非引用同行回执;"
    "新差异如实入茶水间并登记前瞻目标防蒸发;不代 Codex 做落地 commit。"
)


def main():
    proc = subprocess.run(
        [
            sys.executable, TRACE, "open",
            "--level", "L2",
            "--problem", PROBLEM,
            "--success", SUCCESS,
            "--workspace", r"D:\WeilanSkillEvolution",
            "--scope", "skill-evolution",
            "--branch", "main",
            "--relation", "continue",
            "--parent", "wf-20260729-233200-f515e1",
        ],
        capture_output=True,
    )
    sys.stdout.write("rc=%d\n" % proc.returncode)
    sys.stdout.write(proc.stdout.decode("utf-8", errors="replace") + "\n")
    sys.stdout.write(proc.stderr.decode("utf-8", errors="replace") + "\n")


if __name__ == "__main__":
    main()
