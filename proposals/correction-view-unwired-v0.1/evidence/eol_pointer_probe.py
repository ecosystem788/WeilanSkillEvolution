#!/usr/bin/env python3
"""只读探针:把每条更正的 before_hash 在四种 EOL 口径下解析回物理行。

缘起 2026-07-29:FINDING 第二节明写「#8 本回合未诊断出原因,不下结论」。
本探针把那个悬项变成测量——#8 的 before_hash 唯一命中 payload+CR,
即写入时那一行以 CRLF 收尾,而今日工作树是纯 LF,故其前像已不复存在。

零写入:不改账本、不改更正、不产生视图文件。从仓根运行:
    python proposals/correction-view-unwired-v0.1/evidence/eol_pointer_probe.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

IMPL = Path("proposals/bounded-scheduler-v0.1/impl")
RAW = IMPL / "peer-chat.jsonl"
CORRECTIONS = IMPL / "peer-chat.corrections.jsonl"

# 四种口径:裸 payload、payload+CR、payload+LF、payload+CRLF。
# payload = 以 b"\n" 切分后的分片,故在 CRLF 文件上它自带尾随 CR;
# 写方若在 CRLF 工作树上直接对分片取哈希,得到的就是 "+CR" 那一栏。
SUFFIXES = {"": b"", "+CR": b"\r", "+LF": b"\n", "+CRLF": b"\r\n"}


def build_index(raw_path: Path) -> dict[str, tuple[str, int]]:
    index: dict[str, tuple[str, int]] = {}
    for line_number, payload in enumerate(raw_path.read_bytes().split(b"\n"), start=1):
        for label, suffix in SUFFIXES.items():
            digest = hashlib.sha256(payload + suffix).hexdigest()
            index.setdefault(digest, (label, line_number))
    return index


def main() -> int:
    index = build_index(RAW)
    rows = []
    for entry_number, line in enumerate(
        CORRECTIONS.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        record = json.loads(line)
        before_hash = record.get("before_hash")
        if not isinstance(before_hash, str):
            rows.append(
                {
                    "entry": entry_number,
                    "before_hash": None,
                    "resolves_as": "no_before_hash",
                    "kind": record.get("kind") or "batch-redaction",
                }
            )
            continue
        hit = index.get(before_hash)
        rows.append(
            {
                "entry": entry_number,
                "before_hash": before_hash,
                "resolves_as": (
                    "unresolvable" if hit is None else f"line {hit[1]} payload{hit[0]}"
                ),
                "kind": record.get("kind"),
            }
        )

    for row in rows:
        print(
            "#%-3d %-24s %s"
            % (
                row["entry"],
                (row["before_hash"] or "-")[:16],
                row["resolves_as"] + (f"  (kind={row['kind']})" if row["kind"] else ""),
            )
        )
    print()
    print(json.dumps({"raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
