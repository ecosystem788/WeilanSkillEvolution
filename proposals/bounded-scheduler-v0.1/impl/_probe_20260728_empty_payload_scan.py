#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读复跑器：核 Codex 2026-07-28T16:06:24+09:00 判断里的第 (1) 条前提
   ——「全账本实扫只有这一条 Claude 空 text」。

口径（写死，便于别人复跑得到同一答案）：
  * 扫描目录 = 本脚本所在目录下的全部 *.jsonl（不递归）。
  * 逐物理行 json.loads；解析失败单列，不当成空。
  * 「空载荷」= 该行是 JSON object，且其载荷字段存在但 str.strip() == ""。
  * 载荷字段名 = 各账本实际承载人话/意图的键，见 PAYLOAD_KEYS；
    未在表内的键一律不算（避免把 re/reason_codes 之类算进来造假阳）。
  * 只读：不写任何文件、不改任何账本。
退出码恒 0；结论看 stdout 的 JSON。
"""
import json
import sys
from pathlib import Path

# 每个账本里承载「说了什么」的字段。多个 = 任一为空即计入。
PAYLOAD_KEYS = ("text", "description", "note", "reason", "message")

HERE = Path(__file__).resolve().parent


def decode(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8")


def main() -> int:
    empties = []
    parse_errors = []
    totals = {}
    for path in sorted(HERE.glob("*.jsonl")):
        n = 0
        for lineno, line in enumerate(decode(path).splitlines(), start=1):
            if not line.strip():
                continue
            n += 1
            try:
                obj = json.loads(line)
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(
                    {"file": path.name, "line": lineno, "error": str(exc)}
                )
                continue
            if not isinstance(obj, dict):
                continue
            for key in PAYLOAD_KEYS:
                if key in obj and isinstance(obj[key], str) and obj[key].strip() == "":
                    empties.append(
                        {
                            "file": path.name,
                            "line": lineno,
                            "key": key,
                            "from": obj.get("from"),
                            "time": obj.get("time"),
                            "id": obj.get("id"),
                            "keys": sorted(obj.keys()),
                        }
                    )
        totals[path.name] = n

    print(
        json.dumps(
            {
                "scanned_files": len(totals),
                "scanned_lines": sum(totals.values()),
                "per_file_lines": totals,
                "payload_keys": list(PAYLOAD_KEYS),
                "empty_payload_rows": empties,
                "empty_payload_count": len(empties),
                "parse_errors": parse_errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
