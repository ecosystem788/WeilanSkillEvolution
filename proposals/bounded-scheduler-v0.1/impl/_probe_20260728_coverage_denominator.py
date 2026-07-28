#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读复跑器 | 2026-07-28 | 覆盖率检查的分母是否干净

背景:茶水间 2026-07-28T18:31:46+09:00 Codex 把重入清单第 (c) 条收窄为
"以完备键域驱动覆盖:缺席=unclassified,存在=classified",以避开 conflicts_with
那种可选自报通道(实测 0/92 非空)。本脚本量的是:这个形状在本仓已有一个**现役且承重**
的实例(wake_brief.owner_inbox_delta),它的分母今天是不是干净的。

承重口径(先声明,免得读者把方便的数读成结论):
  · 本脚本的承重数是 dangling_overlay_keys / duplicate_overlay_keys /
    rows_missing_id / empty_string_id —— 即"分母与 overlay 的键本身是否可信",
    不是 pending 计数。pending=0 只说明今天没积压,不说明机制健全。
  · replies 一列只做观察,不作判据:协议从未要求 inbox : replies 为 1:1
    (指令类消息可以只 processed 不 reply,一条消息也可能拆成多条回信)。
    列出它是为了展示"同一键域上两个 overlay 覆盖率不同且无一致性检查"这个事实。
  · 全量而非抽样,按存储行计。空行跳过;解析失败逐行记入 parse_errors 而非静默丢弃。

caveat 三条:
  1. 本脚本读 impl/ 平账本,那里没有 sequence 字段、无 reducer、无准入门
     (append_clocked_jsonl.py:59-63 落盘前只检查末尾换行)。故"今天干净"是观察,
     不是被任何机制保证的不变量。
  2. wake_brief 的 delta 判据是 str(row.get("id","")) not in processed。故 inbox 行
     若缺 id,其键为空串:今天 fail-open(留在 delta 里、会被看见);但只要有人往
     processed 写一条 id="" 的行,所有缺 id 的 inbox 行会被一次性静默吞掉。
     empty_string_id 两列就是量这个"未被引爆"的距离。
  3. codex-inbox 一侧的 processed 由 Codex 写,本脚本只读双方文件,不判断谁对。

退出码恒 0:这是量具不是判据,不该因数据难看而让调用方以为脚本坏了。
"""

from __future__ import annotations

import io
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))

# 第四项是 replies 里指回键域的字段名。两侧实测都是 reply_to
# (codex-inbox-replies.jsonl 104 行的键集恒为 from/reply_to/text/time[/time_authority])。
PAIRS = [
    ("owner", "owner-inbox.jsonl", "owner-inbox-processed.jsonl", "owner-inbox-replies.jsonl", "reply_to"),
    ("codex", "codex-inbox.jsonl", "codex-inbox-processed.jsonl", "codex-inbox-replies.jsonl", "reply_to"),
]


def read_rows(name):
    path = os.path.join(ROOT, name)
    rows, errors = [], []
    if not os.path.exists(path):
        return rows, [{"file": name, "error": "missing"}]
    with io.open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append((lineno, json.loads(line)))
            except Exception as exc:  # noqa: BLE001 - 逐行记录,不静默丢弃
                errors.append({"file": name, "line": lineno, "error": str(exc)})
    return rows, errors


def probe():
    report = {"probe": "coverage_denominator", "parse_errors": [], "pairs": []}

    for label, inbox_name, processed_name, replies_name, reply_key in PAIRS:
        inbox, e1 = read_rows(inbox_name)
        processed, e2 = read_rows(processed_name)
        replies, e3 = read_rows(replies_name)
        report["parse_errors"].extend(e1 + e2 + e3)

        # 键域 = inbox 的 id(由生产方签发,分类方不拥有这一列)
        inbox_ids = [str(row.get("id", "")) for _, row in inbox]
        inbox_missing_id = [ln for ln, row in inbox if "id" not in row]
        inbox_empty_id = [ln for (ln, _), key in zip(inbox, inbox_ids) if key == ""]
        domain = set(inbox_ids)

        overlay_ids = [str(row.get("id", "")) for _, row in processed]
        overlay_missing_id = [ln for ln, row in processed if "id" not in row]
        overlay_empty_id = [ln for (ln, _), key in zip(processed, overlay_ids) if key == ""]
        overlay_set = set(overlay_ids)

        dup = sorted(k for k, n in Counter(overlay_ids).items() if n > 1)
        dangling = sorted(overlay_set - domain)
        pending = [k for k in inbox_ids if k not in overlay_set]

        reply_keys = [str(row.get(reply_key, "")) for _, row in replies]
        reply_dangling = sorted({k for k in reply_keys if k and k not in domain})
        unreplied = [k for k in inbox_ids if k not in set(reply_keys)]

        report["pairs"].append({
            "label": label,
            "domain_rows": len(inbox),
            "domain_distinct_keys": len(domain),
            "domain_duplicate_keys": sorted(k for k, n in Counter(inbox_ids).items() if n > 1),
            "overlay_rows": len(processed),
            # —— 承重四项 ——
            "dangling_overlay_keys": dangling,
            "duplicate_overlay_keys": dup,
            "rows_missing_id": {"domain": inbox_missing_id, "overlay": overlay_missing_id},
            "empty_string_id": {"domain": inbox_empty_id, "overlay": overlay_empty_id},
            # —— 观察项,非判据 ——
            "pending_count": len(pending),
            "replies_rows": len(replies),
            "replies_dangling_keys": reply_dangling,
            "domain_keys_without_reply": len(unreplied),
        })

    return report


if __name__ == "__main__":
    print(json.dumps(probe(), ensure_ascii=False, indent=2))
