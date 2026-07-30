"""Read-only census: how long can a *legitimate* open frame sit without a new event?

Motivation: 2026-07-31 the community deadlocked for 7h because a frame lost its
closer mid-round and `assert_closed_parent` has no crash-recovery path. Any
timeout-based self-heal needs an empirical floor for the timeout, otherwise the
threshold is invented. This probe measures the distribution of intra-frame event
gaps over every frame on disk, so a proposed T can be stated as a multiple of the
observed worst legitimate gap rather than as a guess.

It also answers, from the records themselves, whether "the creating process is
gone" is checkable at all: it reports which identity-bearing fields exist on
frame events.

Writes nothing. Prints JSON to stdout.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def state_root() -> Path:
    """Same resolution order as runtime_core.state_root — ask the environment."""
    explicit = os.environ.get("WEILAN_METHOD_HOME")
    if explicit:
        return Path(explicit)
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "method-state"
    return Path.home() / ".weilan-method"


def parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


def main() -> int:
    root = state_root()
    frames_dir = root / "frames"
    if not frames_dir.exists():
        print(json.dumps({"error": "frames dir missing", "root": str(root)}))
        return 1

    identity_keys: dict[str, int] = {}
    closed_gaps: list[tuple[float, str, str, str]] = []
    open_frames: list[dict] = []
    span_by_frame: list[tuple[float, str, int]] = []
    total_events = 0
    frame_count = 0
    unparsed: list[str] = []

    for path in sorted(frames_dir.glob("*/*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:  # unreadable file is a fact, not a crash
            unparsed.append(f"{path.name}: {exc}")
            continue
        events = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                unparsed.append(f"{path.name}: {exc}")
        if not events:
            continue
        frame_count += 1
        total_events += len(events)
        for event in events:
            for key in event:
                if key not in {"data", "schema_version"}:
                    identity_keys[key] = identity_keys.get(key, 0) + 1

        terminal = events[-1].get("event_type")
        stamps = [parse(e["timestamp_utc"]) for e in events]
        gaps = [
            ((stamps[i + 1] - stamps[i]).total_seconds(), events[i].get("event_type", "?"),
             events[i + 1].get("event_type", "?"), path.stem)
            for i in range(len(stamps) - 1)
        ]
        span = (stamps[-1] - stamps[0]).total_seconds()
        if terminal == "frame_closed":
            closed_gaps.extend(gaps)
            span_by_frame.append((span, path.stem, len(events)))
        else:
            open_frames.append(
                {
                    "frame_id": path.stem,
                    "terminal_event_type": terminal,
                    "event_count": len(events),
                    "last_event_utc": events[-1]["timestamp_utc"],
                    "span_seconds": span,
                }
            )

    closed_gaps.sort(reverse=True)
    span_by_frame.sort(reverse=True)
    gap_values = sorted(g[0] for g in closed_gaps)

    def pct(p: float) -> float | None:
        if not gap_values:
            return None
        idx = min(len(gap_values) - 1, int(round(p * (len(gap_values) - 1))))
        return gap_values[idx]

    report = {
        "probe": "frame_gap_census",
        "read_only": True,
        "state_root": str(root),
        "frames_scanned": frame_count,
        "events_scanned": total_events,
        "unparsed": unparsed,
        "identity_bearing_top_level_keys": sorted(identity_keys),
        "actor_identity_present": any(
            key in identity_keys for key in ("actor", "agent", "pid", "host", "hostname", "process_id")
        ),
        "closed_frames": len(span_by_frame),
        "intra_frame_gaps_closed_frames": {
            "count": len(gap_values),
            "max_seconds": gap_values[-1] if gap_values else None,
            "p99_seconds": pct(0.99),
            "p95_seconds": pct(0.95),
            "median_seconds": pct(0.5),
            "top10": [
                {"seconds": round(s, 1), "from": a, "to": b, "frame_id": f}
                for s, a, b, f in closed_gaps[:10]
            ],
        },
        "longest_closed_frame_spans_top10": [
            {"seconds": round(s, 1), "frame_id": f, "events": n} for s, f, n in span_by_frame[:10]
        ],
        "non_closed_frames": open_frames,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
