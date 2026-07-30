"""Read-only: for every closed frame, would a silence-timeout T have fired, and
would it have been wrong?

The first probe (_probe_20260731_frame_gap_census.py) showed the 2026-07-31
deadlock's 7.5h silence is only the 3rd-longest gap on record, which looks like
"a timeout cannot separate a dead round from a slow one". This probe checks that
reading against the close verdicts instead of against the gap ranking: it buckets
every closed frame by its longest intra-frame silence and reports, per candidate
threshold T, how many frames would have been abandoned and how each of them
actually ended.

A frame that exceeded T and closed `success` without a recovery marker is a
measured false positive. That number — not intuition — is what a proposed T has
to be argued from.

Writes nothing. Prints JSON to stdout.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Phrases the community has actually used when force-closing a hung frame.
RECOVERY_MARKERS = re.compile(
    r"孤儿帧|补闭|恢复闭合|解堵|解死锁|interrupted|did not complete|orphan|deadlock|Late close",
    re.IGNORECASE,
)
THRESHOLDS = [900, 1800, 3600, 7200, 10800, 21600]


def state_root() -> Path:
    explicit = os.environ.get("WEILAN_METHOD_HOME")
    if explicit:
        return Path(explicit)
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "method-state"
    return Path.home() / ".weilan-method"


def main() -> int:
    frames_dir = state_root() / "frames"
    rows = []
    for path in sorted(frames_dir.glob("*/*.jsonl")):
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))
        if not events or events[-1].get("event_type") != "frame_closed":
            continue
        stamps = [datetime.fromisoformat(e["timestamp_utc"]) for e in events]
        max_gap = max(
            ((stamps[i + 1] - stamps[i]).total_seconds() for i in range(len(stamps) - 1)),
            default=0.0,
        )
        close_data = events[-1].get("data", {})
        verdict = str(close_data.get("verdict", ""))
        rows.append(
            {
                "frame_id": path.stem,
                "max_gap_seconds": max_gap,
                "event_count": len(events),
                "outcome": close_data.get("outcome"),
                "recovery_marked": bool(RECOVERY_MARKERS.search(verdict)),
                "verdict_head": verdict[:160].replace("\n", " "),
            }
        )

    buckets = {}
    for threshold in THRESHOLDS:
        fired = [r for r in rows if r["max_gap_seconds"] > threshold]
        false_positives = [
            r for r in fired if r["outcome"] == "success" and not r["recovery_marked"]
        ]
        buckets[str(threshold)] = {
            "would_fire_on_frames": len(fired),
            "of_which_closed_failed": sum(1 for r in fired if r["outcome"] == "failed"),
            "of_which_recovery_marked": sum(1 for r in fired if r["recovery_marked"]),
            "measured_false_positives": len(false_positives),
            "false_positive_frames": [
                {
                    "frame_id": r["frame_id"],
                    "gap_seconds": round(r["max_gap_seconds"], 1),
                    "verdict_head": r["verdict_head"],
                }
                for r in false_positives
            ][:10],
        }

    long_rows = sorted(
        (r for r in rows if r["max_gap_seconds"] > 1800),
        key=lambda r: r["max_gap_seconds"],
        reverse=True,
    )
    report = {
        "probe": "long_gap_outcomes",
        "read_only": True,
        "closed_frames_scanned": len(rows),
        "recovery_marker_pattern": RECOVERY_MARKERS.pattern,
        "thresholds": buckets,
        "frames_over_1800s": [
            {
                "frame_id": r["frame_id"],
                "gap_seconds": round(r["max_gap_seconds"], 1),
                "events": r["event_count"],
                "outcome": r["outcome"],
                "recovery_marked": r["recovery_marked"],
                "verdict_head": r["verdict_head"],
            }
            for r in long_rows
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
