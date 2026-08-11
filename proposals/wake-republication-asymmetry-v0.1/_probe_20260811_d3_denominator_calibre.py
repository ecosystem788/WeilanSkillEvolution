#!/usr/bin/env python3
"""_probe_20260811_d3_denominator_calibre.py -- read-only.

D3 (registered unpaid measurement debt in
DESIGN_INPUT_20260811_seat_discharge_key.md sec. 3: "whole line is n = 1 day /
1 scope") plus one denominator-caliber question that D1 left implicit.

Question 1 (caliber):
  peer-chat:3771 reports reverse 25/32 = 78%, forward 29/32 = 91%, and
  DESIGN_INPUT S5 reads the two-key union 32/32 as a "wording coincidence".
  But _probe_20260811_d1_non_anchor_control.py (which reproduces 3771 exactly)
  defines the denominator as  seat := reverse UNION forward.  Under that
  definition union coverage is 100% BY CONSTRUCTION on every window, so
  "32/32 full coverage" carries no information about coverage at all.
  3773 already adopted a wider caliber (union 36 = 32 + 4 section-7.2-only
  frames -- frames that are seat-related yet missed by BOTH keys).
  This probe recomputes every coverage under BOTH denominators.

Question 2 (D3, n):
  Same computation over 7 JST 00:00-07:15 windows + 3 full-day windows,
  instead of the single anchor day.

Method: identical to _probe_20260811_d1_non_anchor_control.py (same frame
universe, same recursive string-leaf text, same seat dictionary, same
regexes, same JST->UTC window arithmetic). Sanity gate: the anchor window
must still reproduce 3771's 67 / 32 / 25 / 29; a mismatch is reported, not
hidden.

Caveat carried into the report: the WIDE denominator is itself keyword-based
(the literal section marker), so it is also a lower bound on the true
seat-related set. Every "miss" number here is therefore a lower bound on the
true miss, never an estimate of it.

DISCIPLINE: never calls wake_brief.py (that would advance the shared
byte-offset cursor). Pure read. Writes nothing except its own stdout.
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

# label, start_utc, end_utc  (JST 00:00-07:15 == UTC (d-1) 15:00-22:15)
WINDOWS = [
    ("anchor-jst-08-11", "2026-08-10T15:00:00+00:00", "2026-08-10T22:15:00+00:00"),
    ("jst-08-10", "2026-08-09T15:00:00+00:00", "2026-08-09T22:15:00+00:00"),
    ("jst-08-09", "2026-08-08T15:00:00+00:00", "2026-08-08T22:15:00+00:00"),
    ("jst-08-08", "2026-08-07T15:00:00+00:00", "2026-08-07T22:15:00+00:00"),
    ("jst-08-07", "2026-08-06T15:00:00+00:00", "2026-08-06T22:15:00+00:00"),
    ("jst-08-06", "2026-08-05T15:00:00+00:00", "2026-08-05T22:15:00+00:00"),
    ("jst-08-05", "2026-08-04T15:00:00+00:00", "2026-08-04T22:15:00+00:00"),
    ("full-jst-08-10", "2026-08-09T15:00:00+00:00", "2026-08-10T15:00:00+00:00"),
    ("full-jst-08-09", "2026-08-08T15:00:00+00:00", "2026-08-09T15:00:00+00:00"),
    ("full-jst-08-08", "2026-08-07T15:00:00+00:00", "2026-08-08T15:00:00+00:00"),
]


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


def load_frames() -> dict:
    frames: dict = {}
    pattern = os.path.join(FRAMES_ROOT, "*", "wf-*.jsonl")
    for path in sorted(glob.glob(pattern)):
        events: list[dict] = []
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
        if not (scope_ok and ws_ok and opened):
            continue
        frames[os.path.basename(path)[: -len(".jsonl")]] = {
            "opened_utc": opened,
            "problem": problem,
            "text": "\n".join(event_text(e) for e in events),
        }
    return frames


def pct(num: int, den: int):
    return round(num / den, 4) if den else None


def classify(frames: dict, start_iso: str, end_iso: str) -> dict:
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    reverse: list[str] = []
    forward: list[str] = []
    s72_only: list[str] = []
    total = 0
    for frame_id, frame in frames.items():
        try:
            ts = datetime.fromisoformat(frame["opened_utc"])
        except ValueError:
            continue
        if not (start <= ts < end):
            continue
        total += 1
        text = frame["text"]
        is_reverse = bool(RE_REVERSE.search(text))
        is_forward = bool(RE_FORWARD.search(text))
        is_s72 = bool(RE_SECTION72.search(text))
        if is_reverse:
            reverse.append(frame_id)
        if is_forward:
            forward.append(frame_id)
        if is_s72 and not is_reverse and not is_forward:
            s72_only.append(frame_id)
    narrow = sorted(set(reverse) | set(forward))
    wide = sorted(set(narrow) | set(s72_only))
    return {
        "total_frames": total,
        "narrow_denominator_union_of_two_keys": len(narrow),
        "wide_denominator_incl_section72_only": len(wide),
        "reverse_hits": len(reverse),
        "forward_hits": len(forward),
        "both_keys_missed": sorted(s72_only),
        "coverage_narrow": {
            "reverse": pct(len(reverse), len(narrow)),
            "forward": pct(len(forward), len(narrow)),
            "union": pct(len(narrow), len(narrow)),
        },
        "coverage_wide": {
            "reverse": pct(len(reverse), len(wide)),
            "forward": pct(len(forward), len(wide)),
            "union": pct(len(narrow), len(wide)),
        },
    }


def main() -> int:
    frames = load_frames()
    out: dict = {
        "probe": "d3_denominator_calibre",
        "scope": SCOPE,
        "frames_loaded": len(frames),
        "calls_wake_brief": False,
        "derived_from": "_probe_20260811_d1_non_anchor_control.py (same method)",
        "windows": {},
    }
    for label, start, end in WINDOWS:
        out["windows"][label] = classify(frames, start, end)

    anchor = out["windows"]["anchor-jst-08-11"]
    out["sanity_vs_3771"] = {
        "expected": {"total": 67, "seat_narrow": 32, "reverse": 25, "forward": 29},
        "probe": {
            "total": anchor["total_frames"],
            "seat_narrow": anchor["narrow_denominator_union_of_two_keys"],
            "reverse": anchor["reverse_hits"],
            "forward": anchor["forward_hits"],
        },
        "matches": anchor["total_frames"] == 67
        and anchor["narrow_denominator_union_of_two_keys"] == 32
        and anchor["reverse_hits"] == 25
        and anchor["forward_hits"] == 29,
    }
    # by-construction check: narrow union coverage is 1.0 on EVERY window
    out["narrow_union_is_one_by_construction"] = all(
        w["coverage_narrow"]["union"] in (None, 1.0) for w in out["windows"].values()
    )
    # spot-check material: what are the both-keys-missed frames about?
    spot: dict = {}
    for label in ("anchor-jst-08-11", "jst-08-09", "jst-08-08"):
        spot[label] = [
            {"frame_id": fid, "problem": (frames.get(fid) or {}).get("problem")}
            for fid in out["windows"][label]["both_keys_missed"]
        ]
    out["both_keys_missed_spotcheck"] = spot

    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
