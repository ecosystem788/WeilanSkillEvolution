#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only forensic probe: find write-order/timestamp inversions in append-only ledgers.

Zero authority. Writes nothing. Reads nothing but the ledger files named on the
command line (defaults below).

Why this exists
---------------
peer_health_wake anchors liveness on ``max(timestamp)`` over ledger entries.
A single entry stamped in the future therefore *persistently* poisons the anchor:
later honest entries cannot pull it back, and the sentinel stays structurally
unable to raise until the wall clock catches up (peer-chat 2026-07-26 01:22:07).
The 2026-07-26 r7 incident is the known occurrence. This probe answers the
question that incident raises but does not settle: **has it happened before?**

What it measures
----------------
For each ledger, in *file order* (= write order for append-only files):

* ``inversion``  -- an entry whose timestamp is older than the running max of all
  entries before it. The entry is *shadowed*: it could not move the anchor.
* ``jump``       -- the entry that established a running max which subsequently
  shadowed >=1 later entry. Reported with how many entries it shadowed and for
  how long (wall time from the jump entry to the last entry it shadowed).
* ``future``     -- an entry whose timestamp is later than ``now``. Only
  meaningful for the current moment, so it is reported separately.

An inversion is not by itself a defect: two agents writing concurrently can
legitimately interleave by a few seconds. The probe therefore reports magnitude,
and ``--min-seconds`` filters out small benign interleavings.

Timestamps in these ledgers are naive local wall-clock strings (host is UTC+9,
matching peer_health_wake's own conversion). Comparisons here are all
ledger-vs-ledger in that same naive frame, except the ``future`` check, which
converts ``now`` into it.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

# Host local offset used by the ledgers and by peer_health_wake's conversion.
LEDGER_UTC_OFFSET_HOURS = 9

DEFAULT_LEDGERS = [
    "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/codex-inbox.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/codex-inbox-replies.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/codex-inbox-processed.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/owner-inbox.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/owner-inbox-replies.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/owner-inbox-processed.jsonl",
]

TIME_KEYS = ("time", "timestamp", "time_utc")


def parse_time(raw):
    if not isinstance(raw, str):
        return None
    text = raw.strip().replace("T", " ")
    for suffix in ("+00:00", "Z"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    text = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def entry_time(obj):
    for key in TIME_KEYS:
        if key in obj:
            parsed = parse_time(obj.get(key))
            if parsed is not None:
                return parsed, key
    return None, None


def scan(path, min_seconds, now_local):
    result = {
        "path": path,
        "exists": os.path.exists(path),
        "lines": 0,
        "timed_entries": 0,
        "parse_errors": [],
        "untimed_lines": [],
        "inversions": [],
        "jumps": [],
        "future_entries": [],
    }
    if not result["exists"]:
        return result

    entries = []
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            result["lines"] += 1
            try:
                obj = json.loads(line)
            except Exception as exc:  # noqa: BLE001 - forensic tool reports, never raises
                result["parse_errors"].append({"line": lineno, "error": str(exc)})
                continue
            if not isinstance(obj, dict):
                result["untimed_lines"].append(lineno)
                continue
            when, key = entry_time(obj)
            if when is None:
                result["untimed_lines"].append(lineno)
                continue
            result["timed_entries"] += 1
            entries.append(
                {
                    "line": lineno,
                    "time": when,
                    "time_key": key,
                    "who": obj.get("from") or obj.get("author") or obj.get("id") or "",
                }
            )

    # Pass 1: running max, find shadowed entries and attribute each to its jump.
    running_max = None
    running_max_idx = None
    shadowed_by = {}
    for idx, item in enumerate(entries):
        if running_max is None or item["time"] > running_max:
            running_max = item["time"]
            running_max_idx = idx
            continue
        delta = (running_max - item["time"]).total_seconds()
        if delta < min_seconds:
            continue
        result["inversions"].append(
            {
                "line": item["line"],
                "time": item["time"].isoformat(sep=" "),
                "who": item["who"],
                "behind_running_max_seconds": round(delta, 3),
                "behind_running_max_hours": round(delta / 3600.0, 4),
                "running_max_time": running_max.isoformat(sep=" "),
                "running_max_line": entries[running_max_idx]["line"],
            }
        )
        shadowed_by.setdefault(running_max_idx, []).append(idx)

    # Pass 2: summarise each jump entry by what it shadowed.
    for jump_idx, victims in sorted(shadowed_by.items()):
        jump = entries[jump_idx]
        last_victim = entries[victims[-1]]
        result["jumps"].append(
            {
                "line": jump["line"],
                "time": jump["time"].isoformat(sep=" "),
                "who": jump["who"],
                "shadowed_entries": len(victims),
                "shadowed_lines": [entries[v]["line"] for v in victims],
                "max_shadow_hours": round(
                    max((jump["time"] - entries[v]["time"]).total_seconds() for v in victims) / 3600.0,
                    4,
                ),
                "shadow_span_ends_at": last_victim["time"].isoformat(sep=" "),
            }
        )

    for item in entries:
        if item["time"] > now_local:
            ahead = (item["time"] - now_local).total_seconds()
            result["future_entries"].append(
                {
                    "line": item["line"],
                    "time": item["time"].isoformat(sep=" "),
                    "who": item["who"],
                    "ahead_of_now_hours": round(ahead / 3600.0, 4),
                }
            )

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--ledger", action="append", default=None,
                        help="ledger path relative to --repo (repeatable); default: the wake ledgers")
    parser.add_argument("--min-seconds", type=float, default=1.0,
                        help="ignore inversions smaller than this (benign concurrent interleaving)")
    parser.add_argument("--now", default=None,
                        help="override 'now' as a naive local timestamp, for fixtures")
    parser.add_argument("--json", action="store_true", help="emit raw JSON")
    args = parser.parse_args()

    if args.now:
        now_local = parse_time(args.now)
        if now_local is None:
            raise SystemExit("--now must be YYYY-MM-DD HH:MM:SS")
    else:
        now_local = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=LEDGER_UTC_OFFSET_HOURS
        )

    ledgers = args.ledger or DEFAULT_LEDGERS
    report = {
        "probe": "timestamp_monotonicity_probe",
        "authority": "none",
        "now_local": now_local.isoformat(sep=" "),
        "ledger_utc_offset_hours": LEDGER_UTC_OFFSET_HOURS,
        "min_seconds": args.min_seconds,
        "ledgers": [scan(os.path.join(args.repo, p), args.min_seconds, now_local) for p in ledgers],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("now(local) = %s   min_seconds = %s" % (report["now_local"], args.min_seconds))
    for led in report["ledgers"]:
        name = os.path.basename(led["path"])
        if not led["exists"]:
            print("\n== %s : MISSING" % name)
            continue
        print(
            "\n== %s : %d lines, %d timed, %d inversions, %d jumps, %d future"
            % (
                name,
                led["lines"],
                led["timed_entries"],
                len(led["inversions"]),
                len(led["jumps"]),
                len(led["future_entries"]),
            )
        )
        if led["parse_errors"]:
            print("   parse_errors: %s" % led["parse_errors"][:5])
        if led["untimed_lines"]:
            print("   untimed lines: %d (first: %s)" % (len(led["untimed_lines"]), led["untimed_lines"][:5]))
        for jump in led["jumps"]:
            print(
                "   JUMP line %d @ %s by %r -> shadowed %d entries, max %.4f h, span ends %s"
                % (
                    jump["line"],
                    jump["time"],
                    jump["who"],
                    jump["shadowed_entries"],
                    jump["max_shadow_hours"],
                    jump["shadow_span_ends_at"],
                )
            )
        for fut in led["future_entries"]:
            print(
                "   FUTURE line %d @ %s by %r -> %.4f h ahead of now"
                % (fut["line"], fut["time"], fut["who"], fut["ahead_of_now_hours"])
            )


if __name__ == "__main__":
    main()
