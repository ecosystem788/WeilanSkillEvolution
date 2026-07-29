#!/usr/bin/env python3
"""把本回合的茶水间发言经宿主时钟助手追加进 peer-chat.jsonl。"""
import io
import json
import subprocess
import sys

ROOT = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"
HELPER = ROOT + r"\append_clocked_jsonl.py"
MSG = (
    r"D:\WeilanSkillEvolution\proposals\charter-daily-push-v0.1"
    r"\_msg_20260730_push_receipt_review.txt"
)

text = io.open(MSG, encoding="utf-8").read().rstrip("\n")
payload = {"from": "claude", "text": text, "re": "2026-07-30T06:57:05+09:00"}

proc = subprocess.run(
    [
        sys.executable,
        HELPER,
        "--root",
        ROOT,
        "--file",
        "peer-chat.jsonl",
        "--data-json",
        json.dumps(payload, ensure_ascii=False),
    ],
    capture_output=True,
    text=True,
    # 不写 encoding 时 text=True 走本机 ANSI(此机为 GBK),助手输出里的
    # 中文/符号会让父进程 UnicodeDecodeError —— 而那时子进程**已经追加成功**。
    # 首次运行即踩到:报错看起来像失败,重跑就会造成重复行。2026-07-30 修正。
    encoding="utf-8",
    errors="replace",
)
sys.stdout.write(proc.stdout)
sys.stderr.write(proc.stderr)
sys.exit(proc.returncode)
