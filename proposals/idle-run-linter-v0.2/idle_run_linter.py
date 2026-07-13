#!/usr/bin/env python3
"""idle_run_linter v0.2: read-only evidence packages for CHARTER section 6.3.

Layer1 keeps the v0.1 trailing self-reported IDLE streak.
Layer2 uses a separate sliding window over all agent frames to catch WORK-class
turns that show no structural delta. It never writes state or drives scheduling.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

AUTO_RE = re.compile(r"^wake receipt [0-9a-f]+: stop=\S+, structure=\d+, queued=\d+\s*$")
IDLE_KEYWORDS = [
    "近空醒",
    "空醒",
    "歇着",
    "无真结构",
    "无新结构",
    "没有真结构",
    "同处打转",
    "只翻搅",
    "no real structure",
    "no progress",
    "rested this",
]
NEGATION_MARKERS = ["不是空醒", "非空醒", "not a spin", "not empty"]

PROPOSAL_TEST_RE = re.compile(
    r"(proposal|proposals/|提案|spec|test|pytest|测试|验证|harness)", re.IGNORECASE
)
FILE_DELTA_RE = re.compile(
    r"(\.py\b|\.md\b|README|file|path|git|新增|改动|修改|文件|路径|created|patched|modified)",
    re.IGNORECASE,
)
JST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class FrameRecord:
    ts_raw: str
    ts: datetime | None
    frame_id: str
    klass: str
    verdict: str
    excerpt: str


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        if "T" in text:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=JST).astimezone(timezone.utc)
    except ValueError:
        return None


def classify(verdict: str | None) -> str:
    if verdict is None:
        return "OPEN"
    v = verdict.strip()
    if AUTO_RE.match(v):
        return "AUTO"
    low = v.lower()
    if any(n in v or n in low for n in NEGATION_MARKERS):
        return "WORK"
    if any(k in v or k.lower() in low for k in IDLE_KEYWORDS):
        return "IDLE"
    return "WORK"


def read_frames(frames_root: str) -> list[FrameRecord]:
    frames: list[FrameRecord] = []
    for path in glob.glob(os.path.join(frames_root, "*", "*.jsonl")):
        opened_ts = ""
        frame_id = os.path.splitext(os.path.basename(path))[0]
        verdict = None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("event_type") == "frame_opened":
                        opened_ts = ev.get("timestamp_utc") or opened_ts
                        frame_id = ev.get("frame_id", frame_id)
                    elif ev.get("event_type") == "frame_closed":
                        verdict = (ev.get("data") or {}).get("verdict")
        except OSError:
            continue

        full = (verdict or "").strip()
        excerpt = full.replace("\n", " ")
        if len(excerpt) > 120:
            excerpt = excerpt[:120] + "..."
        frames.append(
            FrameRecord(
                ts_raw=opened_ts,
                ts=parse_time(opened_ts),
                frame_id=frame_id,
                klass=classify(verdict),
                verdict=full,
                excerpt=excerpt,
            )
        )
    frames.sort(key=lambda r: r.ts or datetime.min.replace(tzinfo=timezone.utc))
    return frames


def read_jsonl_records(path: str) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    exists = os.path.exists(path)
    if not exists:
        return {"path": path, "exists": False, "records": records}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rec["_parsed_time"] = parse_time(rec.get("time") or rec.get("timestamp_utc"))
                rec["_source_ref"] = f"{path}:{line_no}"
                records.append(rec)
    except OSError:
        return {"path": path, "exists": False, "records": []}
    return {"path": path, "exists": True, "records": records}


def read_activity(impl_root: str | None) -> dict[str, Any]:
    if not impl_root:
        return {"loaded": False, "reason": "no_impl_root", "sources": {}}
    sources = {
        "peer_chat": read_jsonl_records(os.path.join(impl_root, "peer-chat.jsonl")),
        "owner_inbox_processed": read_jsonl_records(os.path.join(impl_root, "owner-inbox-processed.jsonl")),
        "codex_inbox_processed": read_jsonl_records(os.path.join(impl_root, "codex-inbox-processed.jsonl")),
    }
    return {"loaded": True, "sources": sources}


def records_between(source: dict[str, Any], start: datetime, end: datetime, predicate=None) -> list[dict[str, Any]]:
    out = []
    for rec in source.get("records", []):
        ts = rec.get("_parsed_time")
        if ts is None or ts < start or ts > end:
            continue
        if predicate and not predicate(rec):
            continue
        out.append(rec)
    return out


def activity_window(
    activity: dict[str, Any],
    frames: list[FrameRecord],
    start_override: datetime | None = None,
) -> dict[str, Any]:
    timed = [f.ts for f in frames if f.ts is not None]
    if not activity.get("loaded"):
        return {"status": "UNKNOWN", "reason": activity.get("reason", "activity_not_loaded")}
    if len(timed) != len(frames):
        return {"status": "UNKNOWN", "reason": "missing_frame_time"}
    sources = activity["sources"]
    if not sources["owner_inbox_processed"]["exists"] or not sources["codex_inbox_processed"]["exists"]:
        return {"status": "UNKNOWN", "reason": "processed_inbox_source_missing"}

    # frame_opened is written at frame close, so a turn's own activity (peer-chat
    # posts, inbox processing) is timestamped BEFORE its own frame_opened. Using
    # min(timed) as the lower bound therefore drops the first window-frame's own
    # activity, biasing no_inbox_delta toward true (false SUSPECTED). When a prior
    # frame boundary is known, extend start back to it so the first frame's own
    # turn work falls inside the window. See v0.2.1 fix (peer-chat 2026-07-11).
    start = start_override if start_override is not None else min(timed)
    end = max(timed)
    peer_posts = records_between(
        sources["peer_chat"],
        start,
        end,
        lambda r: r.get("from") in ("claude", "codex", "owner"),
    )
    owner_proc = records_between(sources["owner_inbox_processed"], start, end)
    codex_proc = records_between(sources["codex_inbox_processed"], start, end)
    return {
        "status": "OK",
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "peer_chat_count": len(peer_posts),
        "owner_inbox_processed_count": len(owner_proc),
        "codex_inbox_processed_count": len(codex_proc),
        "source_refs": {
            "peer_chat": [r["_source_ref"] for r in peer_posts],
            "owner_inbox_processed": [r["_source_ref"] for r in owner_proc],
            "codex_inbox_processed": [r["_source_ref"] for r in codex_proc],
        },
    }


def trailing_idle_streak(frames: list[FrameRecord]) -> tuple[list[FrameRecord], list[FrameRecord]]:
    agent = [f for f in frames if f.klass in ("IDLE", "WORK")]
    streak: list[FrameRecord] = []
    for frame in reversed(agent):
        if frame.klass == "IDLE":
            streak.append(frame)
        else:
            break
    streak.reverse()
    return streak, agent


def verdict_has_structure_ref(frame: FrameRecord) -> tuple[bool, bool]:
    has_proposal_or_test = bool(PROPOSAL_TEST_RE.search(frame.verdict))
    has_file_delta = bool(FILE_DELTA_RE.search(frame.verdict))
    return has_proposal_or_test, has_file_delta


def build_structural_windows(agent: list[FrameRecord], activity: dict[str, Any], size: int) -> list[dict[str, Any]]:
    if size <= 0:
        raise ValueError("structural window size must be positive")
    windows: list[dict[str, Any]] = []
    for index in range(0, max(0, len(agent) - size + 1)):
        window = agent[index : index + size]
        if not all(f.klass == "WORK" for f in window):
            continue
        # Lower-bound the activity window at the frame just before this window so
        # the first window-frame's own-turn activity (timestamped before its
        # frame_opened) is counted. index==0 has no prior boundary, so the
        # earliest window keeps the residual off-by-one (documented in README).
        prev_boundary = agent[index - 1].ts if index > 0 else None
        activity_slice = activity_window(activity, window, start_override=prev_boundary)
        has_proposal_or_test = False
        has_file_delta = False
        for frame in window:
            proposal_or_test, file_delta = verdict_has_structure_ref(frame)
            has_proposal_or_test = has_proposal_or_test or proposal_or_test
            has_file_delta = has_file_delta or file_delta

        if activity_slice["status"] != "OK":
            status = "UNKNOWN"
            reasons = [activity_slice["reason"]]
            no_inbox_delta: bool | None = None
        else:
            inbox_count = (
                activity_slice["owner_inbox_processed_count"]
                + activity_slice["codex_inbox_processed_count"]
            )
            no_inbox_delta = inbox_count == 0
            reasons = []
            if not no_inbox_delta:
                reasons.append("inbox_delta_present")
            if has_proposal_or_test:
                reasons.append("proposal_or_test_ref_present")
            if has_file_delta:
                reasons.append("file_delta_ref_present")
            status = "SUSPECTED" if not reasons else "WORK_EVIDENCE_PRESENT"

        windows.append(
            {
                "status": status,
                "frame_ids": [f.frame_id for f in window],
                "classes": [f.klass for f in window],
                "continuous_work_frames": len(window),
                "no_inbox_delta": no_inbox_delta,
                "no_proposal_or_test_ref": not has_proposal_or_test,
                "no_file_delta_ref": not has_file_delta,
                "activity": activity_slice,
                "reasons": reasons,
            }
        )
    return windows


def analyze(frames_root: str, impl_root: str | None = None, structural_window: int = 3) -> dict[str, Any]:
    frames = read_frames(frames_root)
    streak, agent = trailing_idle_streak(frames)
    activity = read_activity(impl_root)
    counts = {"AUTO": 0, "IDLE": 0, "WORK": 0, "OPEN": 0}
    for frame in frames:
        counts[frame.klass] = counts.get(frame.klass, 0) + 1

    layer1_window = {
        "status": "SUSPECTED" if streak else "CLEAR",
        "suspected_idle_streak": len(streak),
        "frame_ids": [f.frame_id for f in streak],
        "activity": activity_window(activity, streak) if streak else None,
    }
    structural_windows = build_structural_windows(agent, activity, structural_window)
    return {
        "tool": "idle_run_linter/v0.2",
        "authority": "read_only_sensor__not_a_scheduler__does_not_write_control_or_change_wake_cadence",
        "dual_sign": {
            "proposal": "peer-chat 2026-07-11 11:18:34",
            "agreement": "peer-chat 2026-07-11 11:24:30",
        },
        "frames_total": len(frames),
        "class_counts": counts,
        "agent_frames": len(agent),
        "layer1_idle_streak_window": layer1_window,
        "layer2_structural_windows": structural_windows,
        "layer2_structural_suspicions": [w for w in structural_windows if w["status"] == "SUSPECTED"],
        "caveats": [
            "Layer1 window is the trailing IDLE streak; Layer2 window is a separate sliding N over all agent frames.",
            "UNKNOWN is not IDLE and never becomes SUSPECTED.",
            "SUSPECTED is an evidence package only; scheduling changes require a separate proposal.",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="idle-run-linter v0.2 (read-only evidence package)")
    codex_home = os.environ.get("CODEX_HOME")
    default_frames = os.path.join(codex_home, "method-state", "frames") if codex_home else None
    ap.add_argument("--frames-root", default=default_frames)
    ap.add_argument("--impl-root", default=None)
    ap.add_argument("--window", type=int, default=12, help="tail agent frames to print")
    ap.add_argument("--structural-window", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not args.frames_root or not os.path.isdir(args.frames_root):
        print(f"[error] frames-root not found: {args.frames_root}", file=sys.stderr)
        return 2
    result = analyze(args.frames_root, args.impl_root, args.structural_window)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("== idle_run_linter v0.2 (read-only; not a scheduler) ==")
    print(f"frames total: {result['frames_total']}  classes: {result['class_counts']}")
    print(
        "Layer1 IDLE streak: "
        f"{result['layer1_idle_streak_window']['suspected_idle_streak']} "
        f"{result['layer1_idle_streak_window']['frame_ids']}"
    )
    suspects = result["layer2_structural_suspicions"]
    print(f"Layer2 structural SUSPECTED windows: {len(suspects)}")
    for window in suspects[-args.window :]:
        print(f"  - {window['frame_ids']} reasons=none activity={window['activity']}")
    if not suspects:
        evaluated = result["layer2_structural_windows"][-args.window :]
        for window in evaluated:
            print(f"  [{window['status']}] {window['frame_ids']} reasons={window['reasons']}")
    print("caveats:")
    for caveat in result["caveats"]:
        print(f"  - {caveat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
