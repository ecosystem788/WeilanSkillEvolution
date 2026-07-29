"""Read-only: where exactly does each CR sit in the 5 governed ledgers?

The 2026-07-30 FINDING and Codex's re-run both report "13 CR lines". The
entrypoint census finds only 9 records whose terminator is CRLF. This probe
resolves that gap by classifying every CR byte by position.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMPL = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl"

GOVERNED = [
    "peer-chat.jsonl",
    "owner-inbox.jsonl",
    "owner-inbox-replies.jsonl",
    "owner-inbox-processed.jsonl",
    "codex-inbox.jsonl",
]


def physical_records(data: bytes):
    start, index = 0, 0
    while start < len(data):
        newline = data.find(b"\n", start)
        end = len(data) if newline < 0 else newline + 1
        yield index, data[start:end]
        index += 1
        start = end


def main() -> int:
    rows = []
    totals = {"records_containing_cr": 0, "terminator_crlf": 0, "embedded_cr_only": 0}
    for name in GOVERNED:
        path = IMPL / name
        if not path.exists():
            continue
        data = path.read_bytes()
        for index, record in physical_records(data):
            if b"\r" not in record:
                continue
            totals["records_containing_cr"] += 1
            is_crlf = record.endswith(b"\r\n")
            body = record[:-2] if is_crlf else (record[:-1] if record.endswith(b"\n") else record)
            embedded = body.count(b"\r")
            if is_crlf:
                totals["terminator_crlf"] += 1
            if embedded and not is_crlf:
                totals["embedded_cr_only"] += 1
            rows.append(
                {
                    "file": name,
                    "line": index + 1,
                    "terminator_is_crlf": is_crlf,
                    "embedded_cr_count_in_payload": embedded,
                    "payload_head": body[:70].decode("utf-8", errors="replace"),
                }
            )
    json.dump(
        {"totals": totals, "records": rows}, sys.stdout, ensure_ascii=False, indent=2
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
