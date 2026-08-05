#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Read-only census of wake-episode arrivals on the skill-evolution ledger.

Reads only: $CODEX_HOME/method-state/frames/<date>/*.jsonl (append-only frame files).
Writes only: its own .out.json next to this file (caller redirects).

Question it answers, and nothing more:
  For each frame_opened event in the window, what is its `problem` string, when did it
  open/close, and what are the inter-arrival gaps between consecutive opens?

Deliberate non-claims:
  - timestamp_utc here is TOOL-GENERATED (weilan_trace stamps it at write time), NOT the
    hand-written `time` field indicted by ledger-timestamp-authority-v0.1. Still recorded
    as a dependency, not asserted as clock truth.
  - "quiescent" is detected by literal substring in the close verdict; a differently-worded
    no-op episode will NOT be counted. Undercount is the failure mode, not overcount.
"""
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

FRAMES_ROOT = os.path.join(
    os.environ.get("CODEX_HOME", r"D:\CodexData\home"), "method-state", "frames"
)
WINDOW_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def load_events(path):
    out = []
    with io.open(path, encoding="utf-8-sig") as fh:
        for ln, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                out.append(json.loads(raw))
            except Exception as exc:
                out.append({"_unparsed": True, "_line": ln, "_err": str(exc), "_path": path})
    return out


def norm_template(problem):
    """Collapse a problem string to a coarse entry-point template.

    Not a classifier with authority - just a grouping key. Digits/ids stripped.
    """
    p = re.sub(r"[0-9a-f]{6,}", "<hex>", problem)
    p = re.sub(r"\d+", "<n>", p)
    return p[:70]


def main():
    if not os.path.isdir(FRAMES_ROOT):
        print(json.dumps({"error": "frames_root_missing", "path": FRAMES_ROOT}))
        return 2
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)

    frames = {}
    unparsed = []
    for day in sorted(os.listdir(FRAMES_ROOT)):
        day_dir = os.path.join(FRAMES_ROOT, day)
        if not os.path.isdir(day_dir):
            continue
        try:
            day_dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if day_dt < cutoff - timedelta(days=1):
            continue
        for name in sorted(os.listdir(day_dir)):
            if not name.endswith(".jsonl"):
                continue
            fid = name[:-6]
            rec = frames.setdefault(fid, {"frame_id": fid, "day": day})
            for ev in load_events(os.path.join(day_dir, name)):
                if ev.get("_unparsed"):
                    unparsed.append(ev)
                    continue
                et = ev.get("event_type")
                if et == "frame_opened":
                    rec["opened_utc"] = ev.get("timestamp_utc")
                    rec["problem"] = (ev.get("data") or {}).get("problem", "")
                    rec["scope"] = ((ev.get("data") or {}).get("causal") or {}).get("scope")
                    rec["branch"] = ((ev.get("data") or {}).get("causal") or {}).get("branch_id")
                    rec["level"] = ev.get("level")
                elif et == "frame_closed":
                    rec["closed_utc"] = ev.get("timestamp_utc")
                    rec["verdict"] = (ev.get("data") or {}).get("verdict", "")
                    rec["outcome"] = (ev.get("data") or {}).get("outcome", "")
                elif et == "frame_abandoned":
                    rec["abandoned_utc"] = ev.get("timestamp_utc")
                rec.setdefault("event_types", []).append(et)

    rows = []
    for rec in frames.values():
        if not rec.get("opened_utc"):
            continue
        try:
            t = datetime.fromisoformat(rec["opened_utc"])
        except Exception:
            continue
        if t < cutoff:
            continue
        rec["_t"] = t
        rows.append(rec)
    rows.sort(key=lambda r: r["_t"])

    QUIESCENT_MARKERS = ["quiescent", "无新话筒", "无到期", "诚实歇息", "无 raised"]
    for r in rows:
        v = r.get("verdict", "") or ""
        r["quiescent_marker_hit"] = [m for m in QUIESCENT_MARKERS if m in v]
        r["template"] = norm_template(r.get("problem", ""))
        if r.get("closed_utc"):
            try:
                r["duration_s"] = (
                    datetime.fromisoformat(r["closed_utc"]) - r["_t"]
                ).total_seconds()
            except Exception:
                r["duration_s"] = None

    gaps = []
    for a, b in zip(rows, rows[1:]):
        gaps.append(
            {
                "from": a["frame_id"],
                "to": b["frame_id"],
                "gap_s": (b["_t"] - a["_t"]).total_seconds(),
            }
        )

    tmpl = Counter(r["template"] for r in rows)
    quiet = [r for r in rows if r["quiescent_marker_hit"]]
    unclosed = [r for r in rows if not r.get("closed_utc") and not r.get("abandoned_utc")]

    # longest run of consecutive quiescent-marked frames
    best = cur = 0
    best_span = cur_span = []
    for r in rows:
        if r["quiescent_marker_hit"]:
            cur += 1
            cur_span = cur_span + [r["frame_id"]]
            if cur > best:
                best, best_span = cur, list(cur_span)
        else:
            cur, cur_span = 0, []

    gs = sorted(g["gap_s"] for g in gaps)
    out = {
        "probe": "wake_arrival_census",
        "frames_root": FRAMES_ROOT,
        "window_days": WINDOW_DAYS,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "frame_count": len(rows),
        "unparsed_lines": len(unparsed),
        "unclosed_frames": [r["frame_id"] for r in unclosed],
        "quiescent_marked": len(quiet),
        "longest_consecutive_quiescent_run": best,
        "longest_run_frames": best_span,
        "gap_seconds": {
            "n": len(gs),
            "min": gs[0] if gs else None,
            "p25": gs[len(gs) // 4] if gs else None,
            "median": gs[len(gs) // 2] if gs else None,
            "p75": gs[3 * len(gs) // 4] if gs else None,
            "max": gs[-1] if gs else None,
            "under_600s": sum(1 for g in gs if g < 600),
            "under_300s": sum(1 for g in gs if g < 300),
        },
        "templates": [{"template": k, "count": v} for k, v in tmpl.most_common()],
        "rows": [
            {
                "frame_id": r["frame_id"],
                "opened_utc": r["opened_utc"],
                "closed_utc": r.get("closed_utc"),
                "duration_s": r.get("duration_s"),
                "scope": r.get("scope"),
                "branch": r.get("branch"),
                "problem": (r.get("problem") or "")[:100],
                "verdict": (r.get("verdict") or "")[:100],
                "quiescent_marker_hit": r["quiescent_marker_hit"],
            }
            for r in rows
        ],
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
