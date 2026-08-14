#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""helper_lint.py - OS watcher v1 (D2) 契约机检器。

不变量（2026-08-14 双签 peer-chat:4031+4033 落地；改动须双签，与 peer_chat_receipt_lint.py 同模式）：
  1. append_clocked_jsonl.py 支持 --wake-true 且要求 --wake-agent（docstring 同步契约行）。
  2. wake_prompt.md / wake_prompt_codex.md 含 --wake-true / --wake-agent 契约行（三处同步）。
  3. watcher/watcher_sentinel.py 存在，且硬冷却默认钉为 30.0。
  4. watcher/README.md 含服务名 / PID / 三命令 / fail-closed。
  5. watcher/watcher_stats.jsonl 存在（只追加试点账本）。

exit 0 = 全部通过；exit 1 = 有失败项。
用法：
  python helper_lint.py --root <impl>
"""

from __future__ import annotations

import argparse
import json
import os
import sys


REQUIRED_PROMPT_TOKENS = ("--wake-true", "--wake-agent")
REQUIRED_README_TOKENS = (
    "watcher-sentinel-skill-evolution",
    "watcher-skill-evolution.pid",
    "watcher-skill-evolution-start.ps1",
    "fail-closed",
)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return stream.read()
    except OSError:
        return ""


def check_contract(root):
    root = os.path.abspath(root)
    findings = []

    def check(name, ok, detail=""):
        findings.append({"name": name, "ok": bool(ok), "detail": detail})

    helper_src = _read(os.path.join(root, "append_clocked_jsonl.py"))
    check("helper_has_wake_flags", "--wake-true" in helper_src and "--wake-agent" in helper_src)
    docstring = helper_src.split('"""')[1] if helper_src.count('"""') >= 2 else ""
    check("helper_docstring_sync", "--wake-agent" in docstring)

    for name in ("wake_prompt.md", "wake_prompt_codex.md"):
        src = _read(os.path.join(root, name))
        check("prompt_sync_" + name, all(token in src for token in REQUIRED_PROMPT_TOKENS))

    watcher_dir = os.path.join(root, "watcher")
    watcher_src = _read(os.path.join(watcher_dir, "watcher_sentinel.py"))
    check("watcher_script_exists", bool(watcher_src))
    check("watcher_cooldown_pinned_30", "DEFAULT_COOLDOWN_SECONDS = 30.0" in watcher_src)

    readme_src = _read(os.path.join(watcher_dir, "README.md"))
    check("watcher_readme_contract", all(token in readme_src for token in REQUIRED_README_TOKENS))
    check("watcher_stats_ledger", os.path.isfile(os.path.join(watcher_dir, "watcher_stats.jsonl")))

    failures = [item for item in findings if not item["ok"]]
    return {
        "schema": "helper_lint_v0.1",
        "root": root,
        "findings": findings,
        "failure_count": len(failures),
        "ok": not failures,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--root", default=here)
    args = parser.parse_args(argv)
    summary = check_contract(args.root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
