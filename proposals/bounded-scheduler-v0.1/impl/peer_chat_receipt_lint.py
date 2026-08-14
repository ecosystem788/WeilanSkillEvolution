#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""peer_chat_receipt_lint.py — 续帧收据固定短结构的机检器（RECEIPT_CONVENTION v0.1 §五）。

范围：只检 peer-chat.jsonl 中正文以【续帧收据】开头的消息（收据）；其余消息不受约束（4024 edit ⑤）。

硬规则（挡门，exit 1）：
  1. 必需字段齐全：干活 = 帧/父/结果/做了什么/续点；休息 = 帧/父/结果 + 一句话尾巴。
  2. 整条消息正文长度：休息 ≤200 字符 / 干活 ≤600 字符。
  3. 帧号合法：wf-YYYYMMDD-HHMMSS-xxxxxx。
  4. 干活收据必须有 round-notes/<帧号>.md（§四）；自承「笔记 pending」除外（交挂账助手，连续 2 醒规则）。

软上限（报告，不挡门，4024 edit ②）：做了什么 ≤350、续点 ≤150、帧+父+结果 ≤80。

--adoption-after：只对 time >= 该时间戳的收据挡门；更早的收据记 history_out_of_scope
（历史不重写、不计失败，4020 边界）。

账本解析错误（既有损坏行由 peer-chat.corrections.jsonl 治理，如 858/1532/1539）只计数、不挡门；
挡门仅针对范围内收据的结构违规。

用法：
  python peer_chat_receipt_lint.py --ledger peer-chat.jsonl --adoption-after 2026-08-14T17:00:00+09:00
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

PREFIX = "【续帧收据】"
FRAME_RE = re.compile(r"wf-\d{8}-\d{6}-[0-9a-f]{6}")

REQUIRED_WORK = ("帧", "父", "结果", "做了什么", "续点")
REQUIRED_REST = ("帧", "父", "结果")
HARD_CAP = {"work": 600, "rest": 200}
SOFT_CAPS = (("做了什么", 350), ("续点", 150))
SOFT_FRAME_PARENT_RESULT_TOTAL = 80


def parse_receipt(text):
    """Return {kind, fields, tail} for a 【续帧收据】-prefixed message, else None."""
    if not text.startswith(PREFIX):
        return None
    rest = text[len(PREFIX):]
    fields = {}
    tail = []
    for seg in rest.split("|"):
        seg = seg.strip()
        m = re.match(r"^(帧|父|结果|做了什么|续点|笔记)=(.+)$", seg)
        if m:
            fields[m.group(1)] = m.group(2).strip()
        elif seg:
            tail.append(seg)
    kind = "work" if "做了什么" in fields else "rest"
    return {"kind": kind, "fields": fields, "tail": " | ".join(tail)}


def check_message(text, round_notes_dir=None):
    """Machine-check one receipt text. Returns dict or None when out of scope."""
    parsed = parse_receipt(text)
    if parsed is None:
        return None
    result = {
        "kind": parsed["kind"],
        "length": len(text),
        "frame": parsed["fields"].get("帧"),
        "issues": [],
        "soft": [],
        "ok": False,
    }
    fields = parsed["fields"]

    required = REQUIRED_WORK if parsed["kind"] == "work" else REQUIRED_REST
    missing = [k for k in required if not fields.get(k)]
    if missing:
        result["issues"].append("missing_fields=" + ",".join(missing))

    if parsed["kind"] == "rest" and not parsed["tail"]:
        result["issues"].append("rest_sentence_missing")

    if len(text) > HARD_CAP[parsed["kind"]]:
        result["issues"].append(
            "too_long=%d>%d" % (len(text), HARD_CAP[parsed["kind"]])
        )

    frame = fields.get("帧")
    if frame:
        if not FRAME_RE.fullmatch(frame):
            result["issues"].append("bad_frame=" + frame)
    else:
        result["issues"].append("frame_missing")

    if "\n" in text:
        result["soft"].append("contains_newline")

    if parsed["kind"] == "work":
        notes_field = fields.get("笔记", "")
        pending = ("pending" in notes_field.lower()) or ("笔记 pending" in text)
        frame_ok = bool(frame) and FRAME_RE.fullmatch(frame) is not None
        if pending:
            result["soft"].append("notes_pending")
        elif round_notes_dir is not None and frame_ok:
            note_path = os.path.join(round_notes_dir, frame + ".md")
            if not os.path.isfile(note_path):
                result["issues"].append("round_notes_missing=" + frame + ".md")
        elif frame_ok is False:
            result["issues"].append("round_notes_uncheckable_no_frame")

    for key, cap in SOFT_CAPS:
        if key in fields and len(fields[key]) > cap:
            result["soft"].append("%s=%d>%d" % (key, len(fields[key]), cap))
    if all(k in fields for k in ("帧", "父", "结果")):
        total = len(fields["帧"]) + len(fields["父"]) + len(fields["结果"])
        if total > SOFT_FRAME_PARENT_RESULT_TOTAL:
            result["soft"].append("frame_parent_result=%d>%d" % (total, SOFT_FRAME_PARENT_RESULT_TOTAL))

    result["ok"] = not result["issues"]
    return result


def parse_time(value):
    """Parse ISO-with-offset or legacy 'YYYY-MM-DD HH:MM:SS' (treated as UTC)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def read_ledger_rows(ledger_path):
    rows = []
    parse_errors = 0
    with open(ledger_path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append({"line": lineno, "row": json.loads(line)})
            except ValueError:
                parse_errors += 1
    return rows, parse_errors


def scan_ledger(ledger_path, round_notes_dir=None, adoption_after=None):
    """Scan a ledger file; returns the lint summary dict."""
    adoption_dt = parse_time(adoption_after) if adoption_after else None
    rows, parse_errors = read_ledger_rows(ledger_path)
    receipts = []
    failures = []
    soft_violations = 0
    history_out_of_scope = 0
    ignored = 0

    for entry in rows:
        row = entry["row"]
        if not isinstance(row, dict) or not isinstance(row.get("text"), str):
            ignored += 1
            continue
        if not row["text"].startswith(PREFIX):
            ignored += 1
            continue
        msg_time = parse_time(row.get("time"))
        if adoption_dt is not None and (msg_time is None or msg_time < adoption_dt):
            history_out_of_scope += 1
            continue
        res = check_message(row["text"], round_notes_dir=round_notes_dir)
        if res is None:
            ignored += 1
            continue
        res["line"] = entry["line"]
        res["time"] = row.get("time")
        res["from"] = row.get("from")
        receipts.append(res)
        if res["issues"]:
            failures.append(res)
        soft_violations += len(res["soft"])

    return {
        "schema": "peer_chat_receipt_lint_v0.1",
        "ledger": ledger_path,
        "round_notes_dir": round_notes_dir,
        "adoption_after": adoption_after,
        "counts": {
            "receipts_total": len(receipts),
            "work": sum(1 for r in receipts if r["kind"] == "work"),
            "rest": sum(1 for r in receipts if r["kind"] == "rest"),
            "failures": len(failures),
            "soft_violations": soft_violations,
            "history_out_of_scope": history_out_of_scope,
            "ignored_non_receipt": ignored,
            "ledger_parse_errors": parse_errors,
        },
        "failures": failures,
        "ok": not failures,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--ledger", default=os.path.join(here, "peer-chat.jsonl"))
    parser.add_argument("--round-notes", default=None, help="round-notes dir (default: <ledger dir>/round-notes)")
    parser.add_argument("--adoption-after", default=None, help="ISO timestamp; older receipts are out-of-scope history")
    args = parser.parse_args(argv)

    ledger_dir = os.path.dirname(os.path.abspath(args.ledger))
    round_notes_dir = args.round_notes or os.path.join(ledger_dir, "round-notes")
    summary = scan_ledger(args.ledger, round_notes_dir=round_notes_dir, adoption_after=args.adoption_after)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
