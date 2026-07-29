#!/usr/bin/env python3
"""只读探针:证明 PowerShell 会在原生命令 *成功* 之后终止脚本。

背景:2026-07-30 的日推收据(peer-chat.jsonl 2026-07-30T06:57:05+09:00)报告
`git push` 的正常进度输出被 PowerShell 包成 NativeCommandError,使同一脚本的
push 后核验段提前中断。这支探针不碰 git、不碰远端,只用一个必然成功
(exit 0)且必然写 stderr 的原生命令,复现同一形状。

承重结论:$LASTEXITCODE=0 与脚本被终止**同时成立**。即"命令成功了"与
"脚本没走到核验"在脚本内部不可区分——对不可逆动作,一个天真的 catch-retry
会推第二次。

用法:python _probe_20260730_stderr_abort_after_success.py
输出:JSON 到 stdout。不写任何账本、不改任何文件。
"""

import json
import subprocess
import sys

# 三种组合:是否 2>&1 重定向 × ErrorActionPreference。命令固定为
# `cmd /c "echo ... 1>&2"`——保证 exit 0 且只写 stderr。
CASES = [
    {
        "name": "stop_with_redirect",
        "error_action": "Stop",
        "redirect": True,
    },
    {
        "name": "stop_without_redirect",
        "error_action": "Stop",
        "redirect": False,
    },
    {
        "name": "continue_with_redirect",
        "error_action": "Continue",
        "redirect": True,
    },
]

TEMPLATE = (
    "$ErrorActionPreference='{ea}'; $r='post-step-not-reached'; "
    "try {{ $out = cmd /c \"echo progress-to-stderr 1>&2\"{redir}; "
    "$r='post-step-reached' }} "
    "catch {{ $r='aborted:' + $_.Exception.GetType().Name }}; "
    "Write-Output (\"result=\" + $r); "
    "Write-Output (\"lastexit=\" + $LASTEXITCODE)"
)


def run_case(case):
    script = TEMPLATE.format(
        ea=case["error_action"],
        redir=" 2>&1" if case["redirect"] else "",
    )
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    parsed = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "=" in line:
            key, _, value = line.partition("=")
            parsed[key.strip()] = value.strip()
    exit_code = parsed.get("lastexit")
    outcome = parsed.get("result")
    return {
        "case": case["name"],
        "error_action_preference": case["error_action"],
        "stderr_redirected_inside_powershell": case["redirect"],
        "inner_native_exit_code": exit_code,
        "post_step_outcome": outcome,
        # 承重位:退出码 0 且 post 段没走到 —— 成功与中断同时成立。
        # (曾在此把键名写成 post_step_outcome 去查 parsed,永远取到 None,
        #  使这一位恒为 false;2026-07-30 自查修正。)
        "aborted_after_success": (
            exit_code == "0" and str(outcome or "").startswith("aborted:")
        ),
    }


def main():
    results = [run_case(c) for c in CASES]
    out = {
        "probe": "powershell native-stderr abort after successful exit",
        "read_only": True,
        "touches_git_or_remote": False,
        "results": results,
        "boundary": (
            "只证明 PowerShell 在该组合下于 exit 0 之后终止脚本;"
            "不证明 2026-07-30 那次 push 的具体调用逐字如此,"
            "也不证明任何一次 push 实际推了几遍。"
        ),
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
