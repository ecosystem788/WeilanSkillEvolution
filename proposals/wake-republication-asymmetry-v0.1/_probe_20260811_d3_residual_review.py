#!/usr/bin/env python3
"""_probe_20260811_d3_residual_review.py -- read-only.

Companion to _probe_20260811_d3_denominator_calibre.py.

Purpose: every coverage number in the seat-discharge design line uses a
denominator built out of the same keys being evaluated, so union coverage is
1.0 by construction and every "miss" count is a lower bound. The only way to
get a key-INDEPENDENT denominator is to look at the frames that no key
matched and judge them by hand.

This probe dumps, for the anchor window (JST 2026-08-11 00:00-07:15), the
residual frames = total MINUS (reverse | forward | section-7.2-only), with
their opened problem statement and closing verdict, so a reviewer can judge
seat-relatedness without any keyword.

Read-only; never calls wake_brief.py.
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import sys
from datetime import datetime

FRAMES_ROOT = r"D:\CodexData\home\method-state\frames"
SCOPE = "skill-evolution"
WORKSPACE = r"D:\WeilanSkillEvolution"

RE_REVERSE = re.compile(r"cosign-durability")
RE_FORWARD = re.compile(r"5-vs-11|5v11|five-vs-eleven")
RE_SECTION72 = re.compile("\u00a77\\.2")

WINDOW = ("2026-08-10T15:00:00+00:00", "2026-08-10T22:15:00+00:00")


def event_text(event: dict) -> str:
    out: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(key)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            out.append(value)

    walk(event)
    return "\n".join(out)


def main() -> int:
    start = datetime.fromisoformat(WINDOW[0])
    end = datetime.fromisoformat(WINDOW[1])
    residual = []
    matched = 0
    total = 0
    for path in sorted(glob.glob(os.path.join(FRAMES_ROOT, "*", "wf-*.jsonl"))):
        events = []
        with io.open(path, "r", encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
        opened = None
        problem = None
        verdict = None
        scope_ok = False
        ws_ok = False
        for event in events:
            if (event.get("data") or {}).get("causal", {}).get("scope") == SCOPE:
                scope_ok = True
            if event.get("workspace") == WORKSPACE:
                ws_ok = True
            if event.get("event_type") == "frame_opened":
                opened = event.get("timestamp_utc")
                problem = (event.get("data") or {}).get("problem")
            if event.get("event_type") == "frame_closed":
                verdict = (event.get("data") or {}).get("verdict")
        if not (scope_ok and ws_ok and opened):
            continue
        try:
            ts = datetime.fromisoformat(opened)
        except ValueError:
            continue
        if not (start <= ts < end):
            continue
        total += 1
        text = "\n".join(event_text(e) for e in events)
        if RE_REVERSE.search(text) or RE_FORWARD.search(text) or RE_SECTION72.search(text):
            matched += 1
            continue
        residual.append(
            {
                "frame_id": os.path.basename(path)[: -len(".jsonl")],
                "opened_utc": opened,
                "problem": problem,
                "verdict": (verdict or "")[:400],
                "text_chars": len(text),
            }
        )
    out = {
        "probe": "d3_residual_review",
        "window_utc": {"start": WINDOW[0], "end": WINDOW[1]},
        "total_frames": total,
        "matched_by_any_of_three_keys": matched,
        "residual_count": len(residual),
        "residual": sorted(residual, key=lambda r: r["opened_utc"]),
        "calls_wake_brief": False,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
