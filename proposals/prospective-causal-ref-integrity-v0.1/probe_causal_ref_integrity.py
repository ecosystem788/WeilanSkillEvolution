#!/usr/bin/env python3
"""只读复跑器：前瞻账本里 goal.causal_event_id 的可解析性分类。

口径（读这个脚本之前先读这一段，否则数字会被读高一格）：
* 本器**只读**。不写账本、不写仓库、不调用 weilan_trace 的任何写路径。
* 它**自己重放原始 JSONL**，不采信 `prospective-show` 的输出——因为 show 会把
  causal_events 截断到最新 20 条却照常打印全部 goals（weilan_trace.py:3598-3607），
  拿 show 的 causal_events 去解 goal.causal_event_id 会得到假的 DANGLING。
  这一点本身是 FINDING 第四节的内容，也是本器存在的理由之一。
* 分类三类：
    NULL      —— 转换时没带 causal_event_id。合法：collapse 本就可以没有因果事件。
    RESOLVES  —— 带了，且在 causal_event_observed 的 causal_event_id 全集里能解析。
    DANGLING  —— 带了，但在该全集里解析不到。
* 额外做一次**跨命名空间**判定：DANGLING 的 id 是否恰好是某条账本记录的
  顶层 `event_id`。若是，说明它不是随机垃圾，而是取错了命名空间的真 id——
  一个「这个 uuid 在账本里存在吗」的朴素 grep 会对它答 YES。

退出码：0 = 重放成功并已打印分类（**不因发现 DANGLING 而非零**，本器是量器不是闸）。
        非 0 = 重放本身失败（找不到账本 / JSON 坏行），此时任何数字都不可采信。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

# 账本目录 = $CODEX_HOME/method-state/memory/prospective/workspaces/<workspace_key>/<scope_key>
# 这两个 key 是 weilan_trace 对 (workspace, scope) 的哈希，硬编码在这里只为给出默认值；
# 记录自身也带 workspace_key/scope_key，下面会断言一致，写错了会 fail loud 而不是静默量错对象。
DEFAULT_WORKSPACE_KEY = "d431c38105a9a791"
DEFAULT_SCOPE_KEY = "c36aecb1ff20"


def default_ledger_dir() -> str:
    home = os.environ.get("CODEX_HOME")
    if not home:
        return ""
    return os.path.join(
        home, "method-state", "memory", "prospective", "workspaces",
        DEFAULT_WORKSPACE_KEY, DEFAULT_SCOPE_KEY,
    )


def load_records(ledger_dir: str):
    files = sorted(glob.glob(os.path.join(ledger_dir, "*.jsonl")))
    if not files:
        raise SystemExit(f"no ledger shards under {ledger_dir!r}; refusing to report numbers")
    records = []
    for path in files:
        with io.open(path, encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append((os.path.basename(path), lineno, json.loads(line)))
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"unparseable ledger line {path}:{lineno}: {exc}")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger-dir", default=default_ledger_dir())
    parser.add_argument("--workspace-key", default=DEFAULT_WORKSPACE_KEY)
    parser.add_argument("--scope-key", default=DEFAULT_SCOPE_KEY)
    args = parser.parse_args()

    if not args.ledger_dir:
        raise SystemExit("CODEX_HOME unset and --ledger-dir not given")

    records = load_records(args.ledger_dir)

    # 断言量的是对的那本账，否则 key 写错会静默量成空账本。
    for shard, lineno, record in records:
        got = (record.get("workspace_key"), record.get("scope_key"))
        want = (args.workspace_key, args.scope_key)
        if got != want:
            raise SystemExit(f"{shard}:{lineno} belongs to {got}, expected {want}")

    observed = {}          # causal_event_id -> 出处
    ledger_event_ids = {}  # 顶层 event_id -> 出处（用于跨命名空间判定）
    for shard, lineno, record in records:
        ledger_event_ids[record.get("event_id")] = f"{shard}:{lineno}"
        if record.get("event_type") == "causal_event_observed":
            observed[record["data"]["causal_event_id"]] = f"{shard}:{lineno}"

    rows = []
    for shard, lineno, record in records:
        if record.get("event_type") != "goal_transitioned":
            continue
        data = record["data"]
        cid = data.get("causal_event_id")
        if not cid:
            verdict = "NULL"
        elif cid in observed:
            verdict = "RESOLVES"
        else:
            verdict = "DANGLING"
        rows.append({
            "verdict": verdict,
            "state": data.get("state"),
            "goal_ref": data.get("goal_ref"),
            "causal_event_id": cid,
            "at": f"{shard}:{lineno}",
            "resolves_as_ledger_event_id": ledger_event_ids.get(cid) if verdict == "DANGLING" else None,
        })

    counts = {"NULL": 0, "RESOLVES": 0, "DANGLING": 0}
    for row in rows:
        counts[row["verdict"]] += 1

    print(json.dumps({
        "ledger_dir": args.ledger_dir,
        "record_count": len(records),
        "observed_causal_event_count": len(observed),
        "transition_count": len(rows),
        "counts": counts,
        "transitions": rows,
        "authority": "read_only_measurement_never_action_authority",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
