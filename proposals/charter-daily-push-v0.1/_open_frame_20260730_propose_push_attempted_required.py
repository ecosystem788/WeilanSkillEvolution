#!/usr/bin/env python3
"""Open this wake episode's receipt frame (relation=continue)."""

import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"

PROBLEM = (
    "把我 2026-07-30T10:54:55+09:00 复核里那条唯一新差异"
    "(push_authorized_oid.py 的 fail() 把 push_attempted 默认成 False,"
    "等于替忘传的作者断言『没尝试推送』)变成一条可签的窄提案,"
    "范围锁 push_authorized_oid.py 与其测试两文件。"
)
SUCCESS = (
    "缺参调用点逐格数清并自证(不用估计);提案含改什么/为什么/怎么验/怎么回滚;"
    "带至少一条 Codex 11:17 那条没说的新差异;不越过双签自行落地;"
    "基线测试自己跑过一遍。"
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
            "--parent", "wf-20260730-024111-9c6be4",
        ],
        capture_output=True,
    )
    sys.stdout.write("rc=%d\n" % proc.returncode)
    sys.stdout.write(proc.stdout.decode("utf-8", errors="replace") + "\n")
    sys.stdout.write(proc.stderr.decode("utf-8", errors="replace") + "\n")


if __name__ == "__main__":
    main()
