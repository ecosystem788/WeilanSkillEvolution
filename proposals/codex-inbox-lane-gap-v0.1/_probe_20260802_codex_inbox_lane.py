#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Read-only probe: does the shared wake brief have a codex-inbox lane, and did
Codex's wake runs read that queue at source?

Nothing here writes to the ledger, the inboxes, or method-state. It only reads
files and prints one JSON object (also written to the .out.json sibling).

Re-run:
  python proposals/codex-inbox-lane-gap-v0.1/_probe_20260802_codex_inbox_lane.py
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import io
import json
import os
import re
import sys

IMPL = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"
INSTALLED = [
    r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\wake_brief.py",
    r"D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py",
    os.path.join(IMPL, "wake_brief.py"),
]
RUNS = os.path.join(IMPL, "wake-codex-runs")


def sha256(path: str) -> dict:
    if not os.path.exists(path):
        return {"path": path, "exists": False}
    data = open(path, "rb").read()
    return {
        "path": path,
        "exists": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def read_jsonl(path: str) -> list:
    rows = []
    if not os.path.exists(path):
        return rows
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def parse_time(value):
    if not value:
        return None
    text = str(value).strip().replace(" ", "T", 1)
    try:
        stamp = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:  # legacy rows: assume host offset (+09:00)
        stamp = stamp.replace(tzinfo=dt.timezone(dt.timedelta(hours=9)))
    return stamp


def decode_run(path: str) -> str:
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def run_commands(text: str):
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        item = obj.get("item") or {}
        if item.get("type") == "command_execution":
            yield item.get("command", "")


def main() -> int:
    out = {"probe": "codex-inbox-lane-gap", "read_only": True}

    # 1. Does the shared brief mechanism know about the codex work queue at all?
    src = io.open(INSTALLED[0], encoding="utf-8").read()
    out["brief_binary"] = [sha256(p) for p in INSTALLED]
    out["brief_all_copies_identical"] = len({h.get("sha256") for h in out["brief_binary"] if h.get("exists")}) == 1
    out["brief_mentions"] = {
        "codex-inbox.jsonl": len(re.findall(r"codex-inbox\.jsonl", src)),
        "codex-inbox-replies.jsonl": len(re.findall(r"codex-inbox-replies\.jsonl", src)),
        "codex-inbox-processed.jsonl": len(re.findall(r"codex-inbox-processed\.jsonl", src)),
    }
    lane_block = src[src.find("brief = {"):src.find("brief = {") + 1600]
    out["brief_lane_keys"] = re.findall(r'^\s{8}"(\w+)":', lane_block, re.M)
    out["brief_has_codex_inbox_lane"] = any("codex_inbox" == k for k in out["brief_lane_keys"])
    fp = src[src.find("def site_fingerprint_for"):src.find("def build_brief")]
    match = re.search(r'"inbox_has_work":\s*bool\(brief\.get\("(\w+)"\)\)', fp)
    out["fingerprint_inbox_has_work_reads"] = match.group(1) if match else None

    # 2. What the prompts promise the brief delivers.
    prompts = {}
    for name in ("wake_prompt_codex.md", "wake_prompt.md"):
        path = os.path.join(IMPL, name)
        text = io.open(path, encoding="utf-8").read()
        line = next((ln.strip() for ln in text.splitlines() if ln.strip().startswith("一次拿到")), None)
        prompts[name] = {"brief_promise_line": line}
    out["prompt_promises"] = prompts

    # 3. Current queue state at source (stateless id-diff, the owner-inbox convention).
    inbox = read_jsonl(os.path.join(IMPL, "codex-inbox.jsonl"))
    processed = read_jsonl(os.path.join(IMPL, "codex-inbox-processed.jsonl"))
    done = {str(r.get("id")) for r in processed if r.get("id")}
    pending = [r for r in inbox if str(r.get("id", "")) not in done]
    out["queue_now"] = {
        "inbox_rows": len(inbox),
        "processed_rows": len(processed),
        "pending_ids": [r.get("id") for r in pending],
        "pending_times": [r.get("time") for r in pending],
    }

    # 4. Per-run: was work pending when the run started, and did the run read the queue?
    processed_at = {}
    for row in processed:
        rid = str(row.get("id"))
        stamp = parse_time(row.get("time"))
        if rid and (rid not in processed_at or (stamp and processed_at[rid] and stamp < processed_at[rid])):
            processed_at[rid] = stamp
    posted_at = {str(r.get("id")): parse_time(r.get("time")) for r in inbox if r.get("id")}

    rows = []
    for path in sorted(glob.glob(os.path.join(RUNS, "2026-08-02*.jsonl"))):
        started = parse_time(os.path.basename(path)[:-6].replace("T", " ").replace("-", ":", 0))
        stem = os.path.basename(path)[:-6]
        started = parse_time(stem[:10] + "T" + stem[11:].replace("-", ":"))
        text = decode_run(path)
        cmds = list(run_commands(text))
        direct = any(re.search(r"codex-inbox\.jsonl", c) for c in cmds)
        brief = any("wake_brief" in c for c in cmds)
        pending_then = [
            rid for rid, posted in posted_at.items()
            if posted and started and posted <= started
            and (rid not in processed_at or (processed_at[rid] and processed_at[rid] > started))
        ]
        rows.append({
            "run": os.path.basename(path),
            "started": started.isoformat() if started else None,
            "read_codex_inbox_at_source": direct,
            "ran_wake_brief": brief,
            "pending_ids_at_start": pending_then,
            "mentions_pending_id_anywhere": {rid: text.count(rid) for rid in pending_then},
        })
    out["runs_today"] = rows
    out["runs_that_skipped_source_read"] = [r["run"] for r in rows if not r["read_codex_inbox_at_source"]]
    out["skipped_with_pending_work"] = [
        r["run"] for r in rows
        if not r["read_codex_inbox_at_source"] and r["pending_ids_at_start"]
    ]

    text = json.dumps(out, ensure_ascii=False, indent=2)
    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    io.open(dest, "w", encoding="utf-8").write(text + "\n")
    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
