"""Claude wake producer for the zero-authority Codex liveness sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from peer_health import check_peer_liveness


WAKE_BRIEF_IMPL = Path(__file__).resolve().parents[1] / "bounded-scheduler-v0.1" / "impl"
if str(WAKE_BRIEF_IMPL) not in sys.path:
    sys.path.insert(0, str(WAKE_BRIEF_IMPL))
from wake_brief import _physical_records, _record_payload, parse_diagnostic  # noqa: E402


LOCAL_TZ = timezone(timedelta(hours=9))
ACTIVITY_FILES = ("codex-inbox-replies.jsonl", "peer-chat.jsonl")
CLAUDE_ACTIVITY_RUNS = "wake-agent-runs"
CODEX_HEARTBEAT_RUNS = "wake-codex-runs"
ORPHAN_STREAK_MINIMUM = 10
_STALE_HEAD = re.compile(r'(?:stage=|"stage"\s*:\s*")frame_open_stale_head')
_ATTEMPTED_PARENT = re.compile(r'(?:attempted_parent=|"attempted_parent"\s*:\s*")(?P<parent>wf-[0-9A-Za-z-]+)')


class CheckResult(list[dict]):
    """List-compatible result with an observable check report for the CLI."""

    def __init__(
        self,
        appended=(),
        *,
        parse_errors: list[dict] | None = None,
        skipped: dict | None = None,
        activity_anchor: dict | None = None,
    ) -> None:
        super().__init__(appended)
        self.parse_errors = parse_errors or []
        self.skipped = skipped
        self.activity_anchor = activity_anchor


def _rows(path: Path, *, parse_errors: list[dict] | None = None) -> list[tuple[int, dict]]:
    if not path.exists():
        return []
    result = []
    for line_index, byte_offset, record_bytes in _physical_records(path.read_bytes()):
        number = line_index + 1
        payload = _record_payload(record_bytes)
        if not payload.strip():
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            if parse_errors is None:
                raise
            parse_errors.append(
                parse_diagnostic(
                    path, number, "decode_failure", f"{type(exc).__name__}: {exc}", record_bytes, byte_offset
                )
            )
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError as exc:
            if parse_errors is None:
                raise
            parse_errors.append(
                parse_diagnostic(
                    path, number, "invalid_json", f"{type(exc).__name__}: {exc}", record_bytes, byte_offset
                )
            )
            continue
        if not isinstance(row, dict):
            exc = TypeError("JSONL row must be an object")
            if parse_errors is None:
                raise exc
            parse_errors.append(
                parse_diagnostic(
                    path, number, "not_object", f"{type(exc).__name__}: {exc}", record_bytes, byte_offset
                )
            )
            continue
        result.append((number, row))
    return result


def _local_time_as_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("activity time is missing")
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return parsed.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def _run_stamp_as_utc(path: Path) -> datetime:
    parsed = datetime.strptime(path.stem, "%Y-%m-%dT%H-%M-%S")
    return parsed.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def _claude_activity_anchor(root: Path, parse_errors: list[dict]) -> tuple[datetime, str] | None:
    activities: list[tuple[datetime, str]] = []
    for line_number, row in _rows(root / "peer-chat.jsonl", parse_errors=parse_errors):
        if row.get("from") == "claude":
            stamp = _local_time_as_utc(row.get("time"))
            activities.append((stamp, f"peer-chat.jsonl:{line_number}@{row['time']} (claude activity)"))
    for line_number, row in _rows(root / "concurrent-receipts.jsonl", parse_errors=parse_errors):
        if str(row.get("wake_id", "")).startswith("claude-"):
            stamp = _local_time_as_utc(row.get("time"))
            activities.append((stamp, f"concurrent-receipts.jsonl:{line_number}@{row['time']} (claude wake)"))
    for path in (root / CLAUDE_ACTIVITY_RUNS).glob("*.json"):
        stamp = _run_stamp_as_utc(path)
        activities.append((stamp, f"{CLAUDE_ACTIVITY_RUNS}/{path.name} (claude wake run)"))
    return max(activities, key=lambda item: item[0]) if activities else None


def _codex_heartbeats_after(root: Path, anchor: datetime) -> list[Path]:
    heartbeats = []
    for path in (root / CODEX_HEARTBEAT_RUNS).glob("*.jsonl"):
        if _run_stamp_as_utc(path) > anchor:
            heartbeats.append(path)
    return sorted(heartbeats, key=_run_stamp_as_utc)


def run_reverse_check(
    *, root: Path, now: datetime | None = None, threshold_hours: float = 4, min_heartbeats: int = 3
) -> CheckResult:
    """Let an awake Codex notice prolonged Claude silence; change no authority."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if threshold_hours <= 0 or min_heartbeats < 1:
        raise ValueError("threshold_hours and min_heartbeats must be positive")

    parse_errors: list[dict] = []
    try:
        anchor = _claude_activity_anchor(root, parse_errors)
        if anchor is None:
            return CheckResult(parse_errors=parse_errors)
        last_activity, source_ref = anchor
        heartbeats = _codex_heartbeats_after(root, last_activity)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        return CheckResult(parse_errors=parse_errors, skipped={"reason": f"{type(exc).__name__}: {exc}"})

    activity_anchor = {"time_utc": last_activity.isoformat(), "source_ref": source_ref}
    silence_hours = (now.astimezone(timezone.utc) - last_activity).total_seconds() / 3600
    if silence_hours < threshold_hours or len(heartbeats) < min_heartbeats:
        return CheckResult(parse_errors=parse_errors, activity_anchor=activity_anchor)

    incident_suffix = hashlib.sha256(last_activity.isoformat().encode("utf-8")).hexdigest()[:12]
    incident_key = f"claude_silence:{incident_suffix}"
    alerts_path = root / "peer-health-alerts.jsonl"
    for _, row in _rows(alerts_path, parse_errors=parse_errors):
        if (
            row.get("direction") == "codex_to_claude"
            and row.get("incident_key") == incident_key
            and row.get("event") in {"raised", "reopened"}
        ):
            return CheckResult(parse_errors=parse_errors, activity_anchor=activity_anchor)

    event = {
        "id": uuid.uuid4().hex[:12],
        "time": now.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "event": "raised",
        "kind": "peer_silence",
        "direction": "codex_to_claude",
        "raised_by": "codex",
        "peer": "claude",
        "status": "suspected",
        "incident_key": incident_key,
        "silence": {
            "last_activity_utc": last_activity.isoformat(),
            "source_ref": source_ref,
            "silence_hours": round(silence_hours, 3),
            "threshold_hours": threshold_hours,
        },
        "observer_heartbeats": {
            "count": len(heartbeats),
            "minimum": min_heartbeats,
            "source_ref": f"{CODEX_HEARTBEAT_RUNS}/ filenames after activity anchor",
        },
        "authority": "none",
        "note": "Claude may be unavailable; verify sources and go ask after her. This is not a fault assertion.",
    }
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    with alerts_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return CheckResult([event], parse_errors=parse_errors, activity_anchor=activity_anchor)


def _orphan_frame_alert(*, root: Path, now: datetime) -> list[dict]:
    """Alert on only the terminal same-parent stale-head suffix; repair nothing."""
    log_path = root / "wake-cron.log"
    if not log_path.exists():
        return []

    streak: list[tuple[str, str]] = []
    parent: str | None = None
    for line in reversed(log_path.read_text(encoding="utf-8").splitlines()):
        match = _ATTEMPTED_PARENT.search(line)
        if not _STALE_HEAD.search(line) or match is None:
            break
        line_parent = match.group("parent")
        if parent is None:
            parent = line_parent
        elif line_parent != parent:
            break
        stamp = line.split(maxsplit=1)[0]
        streak.append((stamp, line_parent))

    if parent is None or len(streak) < ORPHAN_STREAK_MINIMUM:
        return []

    alerts_path = root / "peer-health-alerts.jsonl"
    previous = None
    for _, row in _rows(alerts_path):
        if row.get("kind") == "orphan_frame" and row.get("parent_frame_id") == parent:
            previous = row
    if previous and previous.get("event") in {"raised", "reopened"}:
        return []

    chronological = list(reversed(streak))
    event = {
        "id": uuid.uuid4().hex[:12],
        "time": now.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "event": "reopened" if previous and previous.get("event") == "resolved" else "raised",
        "kind": "orphan_frame",
        "status": "suspected",
        "incident_key": f"orphan_frame:{parent}",
        "parent_frame_id": parent,
        "first_error_time": chronological[0][0],
        "last_error_time": chronological[-1][0],
        "consecutive_count": len(chronological),
        "source_ref": "wake-cron.log terminal suffix",
        "authority": "none",
    }
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    with alerts_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return [event]


def run_check(*, root: Path, now: datetime | None = None, threshold_hours: float = 6) -> CheckResult:
    """Run one check; malformed relevant activity makes the whole check fail safe."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    orphan_alerts = _orphan_frame_alert(root=root, now=now)

    parse_errors: list[dict] = []
    activities: list[tuple[datetime, str]] = []
    try:
        for name in ACTIVITY_FILES:
            path = root / name
            for line_number, row in _rows(path, parse_errors=parse_errors):
                if row.get("from") != "codex":
                    continue
                stamp = _local_time_as_utc(row.get("time"))
                activities.append((stamp, f"{name}:{line_number}@{row['time']} (codex activity)"))
    except (OSError, UnicodeError) as exc:
        return CheckResult(
            orphan_alerts,
            parse_errors=parse_errors,
            skipped={
                "reason": f"{type(exc).__name__}: {exc}",
                "source": path.name,
            },
        )
    except (ValueError, TypeError):
        return CheckResult(orphan_alerts, parse_errors=parse_errors)

    # With no trustworthy activity anchor, silence cannot be measured.
    if not activities:
        return CheckResult(orphan_alerts, parse_errors=parse_errors)
    last_activity, activity_source_ref = max(activities, key=lambda item: item[0])
    activity_anchor = {
        "time_utc": last_activity.isoformat(),
        "source_ref": activity_source_ref,
    }

    try:
        inbox_ids = {
            str(row["id"])
            for _, row in _rows(root / "codex-inbox.jsonl", parse_errors=parse_errors)
            if row.get("id") is not None
        }
        replied_ids = {
            str(row["reply_to"])
            for _, row in _rows(root / "codex-inbox-replies.jsonl", parse_errors=parse_errors)
            if row.get("reply_to") is not None
        }
    except (OSError, UnicodeError) as exc:
        return CheckResult(
            orphan_alerts,
            parse_errors=parse_errors,
            skipped={
                "reason": f"{type(exc).__name__}: {exc}",
                "source": "codex-inbox.jsonl/codex-inbox-replies.jsonl",
            },
            activity_anchor=activity_anchor,
        )
    except TypeError:
        return CheckResult(orphan_alerts, parse_errors=parse_errors, activity_anchor=activity_anchor)

    pending = sorted(inbox_ids - replied_ids)
    return CheckResult(
        orphan_alerts + check_peer_liveness(
            alerts_path=root / "peer-health-alerts.jsonl",
            peer="codex",
            raised_by="claude",
            now=now.astimezone(timezone.utc),
            last_activity_utc=last_activity,
            activity_source_ref=activity_source_ref,
            threshold_hours=threshold_hours,
            pending_item_ids=pending,
            backlog_source_ref="codex-inbox.jsonl ids minus codex-inbox-replies.jsonl reply_to ids",
        ),
        parse_errors=parse_errors,
        activity_anchor=activity_anchor,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--threshold-hours", type=float)
    parser.add_argument(
        "--direction", choices=("claude-to-codex", "codex-to-claude"), default="claude-to-codex"
    )
    parser.add_argument("--min-heartbeats", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        if args.direction == "codex-to-claude":
            threshold = 4 if args.threshold_hours is None else args.threshold_hours
            appended = run_reverse_check(
                root=args.root, threshold_hours=threshold, min_heartbeats=args.min_heartbeats
            )
        else:
            threshold = 6 if args.threshold_hours is None else args.threshold_hours
            appended = run_check(root=args.root, threshold_hours=threshold)
    except (OSError, ValueError) as exc:
        print(f"peer-health check skipped: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "check": "skipped" if appended.skipped else "completed",
                "appended": list(appended),
                "parse_errors": appended.parse_errors,
                "skipped": appended.skipped,
                "activity_anchor": appended.activity_anchor,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
