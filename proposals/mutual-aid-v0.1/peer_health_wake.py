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

from peer_health import check_peer_liveness, export_sentinel_alerts


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
_FRAME_OPEN_FAMILY = re.compile(r'(?:stage=|"stage"\s*:\s*")frame_open(?:_stale_head)?')
_CAUSAL_PARENT_TERMINAL = re.compile(r'causal parent must be terminal')
_ATTEMPTED_PARENT = re.compile(r'(?:attempted_parent=|"attempted_parent"\s*:\s*")(?P<parent>wf-[0-9A-Za-z-]+)')
_RAW_TIME = re.compile(r'"time"\s*:\s*"(?P<time>[^"\\]*(?:\\.[^"\\]*)*)"')
_SHA256 = re.compile(r"[0-9a-f]{64}")


class CheckResult(list[dict]):
    """List-compatible result with an observable check report for the CLI."""

    def __init__(
        self,
        appended=(),
        *,
        parse_errors: list[dict] | None = None,
        known_corrected: list[dict] | None = None,
        skipped: dict | None = None,
        activity_anchor: dict | None = None,
        clock_anomaly: dict | None = None,
    ) -> None:
        super().__init__(appended)
        self.parse_errors = parse_errors or []
        self.known_corrected = known_corrected or []
        self.skipped = skipped
        self.activity_anchor = activity_anchor
        self.clock_anomaly = clock_anomaly


def _current_record_minus_lf_v1(record_bytes: bytes) -> bytes:
    """Remove exactly one trailing LF byte while preserving any stored CR."""
    return record_bytes[:-1] if record_bytes.endswith(b"\n") else record_bytes


def _known_correction(
    *,
    text: str,
    record_bytes: bytes,
    diagnostic: dict,
    corrections: list[tuple[int, dict]],
    corrections_path: Path,
) -> dict | None:
    """Return a zero-authority summary only for an exact time+physical-hash match."""
    time_match = _RAW_TIME.search(text)
    if time_match is None:
        return None
    try:
        record_time = json.loads(f'"{time_match.group("time")}"')
    except json.JSONDecodeError:
        return None

    payload_hash = hashlib.sha256(_current_record_minus_lf_v1(record_bytes)).hexdigest()
    physical_hash = str(diagnostic.get("raw_bytes_sha256", ""))
    for correction_line, correction in corrections:
        if correction.get("corrects") != record_time:
            continue
        before_hash = correction.get("before_hash")
        sentinel_hash = correction.get("sentinel_equiv_hash")
        if isinstance(before_hash, str) and _SHA256.fullmatch(before_hash) and before_hash == payload_hash:
            matched_convention = "remove exactly one trailing LF byte; stored CR preserved"
            matched_hash = before_hash
        elif (
            isinstance(sentinel_hash, str)
            and _SHA256.fullmatch(sentinel_hash)
            and sentinel_hash == physical_hash
        ):
            matched_convention = "sentinel_equiv_hash=sha256(physical record bytes, including line terminator)"
            matched_hash = sentinel_hash
        else:
            continue
        return {
            "source": diagnostic["source"],
            "line": diagnostic["line"],
            "raw_bytes_sha256": physical_hash,
            "matched_hash": matched_hash,
            "matched_convention": matched_convention,
            "corrects": record_time,
            "correction_ref": f"{corrections_path.as_posix()}:{correction_line}",
            "authority": "none",
        }
    return None


def _rows(
    path: Path,
    *,
    parse_errors: list[dict] | None = None,
    corrections: list[tuple[int, dict]] | None = None,
    corrections_path: Path | None = None,
    known_corrected: list[dict] | None = None,
) -> list[tuple[int, dict]]:
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
            diagnostic = parse_diagnostic(
                path, number, "invalid_json", f"{type(exc).__name__}: {exc}", record_bytes, byte_offset
            )
            correction = None
            if corrections is not None and corrections_path is not None and known_corrected is not None:
                correction = _known_correction(
                    text=text,
                    record_bytes=record_bytes,
                    diagnostic=diagnostic,
                    corrections=corrections,
                    corrections_path=corrections_path,
                )
            if correction is None:
                parse_errors.append(diagnostic)
            else:
                known_corrected.append(correction)
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
    normalized = value.strip()
    try:
        parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise ValueError("activity time offset is missing")
        return parsed.astimezone(timezone.utc)
    return parsed.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def _row_is_clocked(row: Mapping[str, object]) -> bool:
    if row.get("time_authority") != "clock":
        return False
    raw = row.get("time")
    if not isinstance(raw, str):
        return False
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError:
        return False
    return parsed.tzinfo is not None

def _run_stamp_as_utc(path: Path) -> datetime:
    parsed = datetime.strptime(path.stem, "%Y-%m-%dT%H-%M-%S")
    return parsed.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def _decode_codex_run(path: Path, parse_errors: list[dict]) -> str | None:
    """Decode one Codex run by its BOM; unreadable runs are visible but never active."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        parse_errors.append(
            parse_diagnostic(
                path,
                1,
                "read_failure",
                f"{type(exc).__name__}: {exc}",
                b"",
                0,
            )
        )
        return None

    if raw.startswith(b"\xff\xfe"):
        encoding = "utf-16"
    elif raw.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    else:
        encoding = "utf-8"
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError as exc:
        parse_errors.append(
            parse_diagnostic(
                path,
                1,
                "decode_failure",
                f"{type(exc).__name__}: {exc}",
                raw,
                0,
            )
        )
        return None


def _codex_run_is_authentic(path: Path, parse_errors: list[dict]) -> bool:
    """Require evidence that the model executed, rather than evidence that cron fired."""
    text = _decode_codex_run(path, parse_errors)
    if text is None:
        return False

    authentic = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            parse_errors.append(
                parse_diagnostic(
                    path,
                    line_number,
                    "invalid_json",
                    f"{type(exc).__name__}: {exc}",
                    line.encode("utf-8", errors="replace"),
                    0,
                )
            )
            continue
        if not isinstance(row, dict):
            parse_errors.append(
                parse_diagnostic(
                    path,
                    line_number,
                    "not_object",
                    "TypeError: JSONL row must be an object",
                    line.encode("utf-8", errors="replace"),
                    0,
                )
            )
            continue
        if row.get("type") == "turn.completed":
            authentic = True
            continue
        if row.get("type") != "item.completed":
            continue
        item = row.get("item")
        item_type = item.get("type") if isinstance(item, dict) else None
        if isinstance(item_type, str) and item_type != "error":
            authentic = True
    return authentic


def _newest_authentic_codex_run(
    root: Path, parse_errors: list[dict]
) -> tuple[datetime, str] | None:
    """Open runs newest-to-oldest and stop at the newest model-executed run."""
    runs = sorted(
        (root / CODEX_HEARTBEAT_RUNS).glob("*.jsonl"),
        key=_run_stamp_as_utc,
        reverse=True,
    )
    for path in runs:
        if _codex_run_is_authentic(path, parse_errors):
            return (
                _run_stamp_as_utc(path),
                f"{CODEX_HEARTBEAT_RUNS}/{path.name} (codex executed run)",
            )
    return None


def _claude_activity_anchor(
    root: Path,
    parse_errors: list[dict],
    known_corrected: list[dict],
    corrections: list[tuple[int, dict]],
    corrections_path: Path,
    now_utc: datetime,
) -> tuple[datetime, str] | None:
    activities: list[tuple[datetime, str]] = []
    peer_chat_head: tuple[int, dict] | None = None
    for line_number, row in _rows(
        root / "peer-chat.jsonl",
        parse_errors=parse_errors,
        corrections=corrections,
        corrections_path=corrections_path,
        known_corrected=known_corrected,
    ):
        if row.get("from") == "claude":
            peer_chat_head = (line_number, row)
    if peer_chat_head is not None:
        line_number, row = peer_chat_head
        stamp = _local_time_as_utc(row.get("time"))
        if _row_is_clocked(row) or stamp <= now_utc:
            activities.append(
                (stamp, f"peer-chat.jsonl:{line_number}@{row['time']} (claude activity)")
            )

    receipt_head: tuple[int, dict] | None = None
    for line_number, row in _rows(root / "concurrent-receipts.jsonl", parse_errors=parse_errors):
        if str(row.get("wake_id", "")).startswith("claude-"):
            receipt_head = (line_number, row)
    if receipt_head is not None:
        line_number, row = receipt_head
        stamp = _local_time_as_utc(row.get("time"))
        if _row_is_clocked(row) or stamp <= now_utc:
            activities.append(
                (stamp, f"concurrent-receipts.jsonl:{line_number}@{row['time']} (claude wake)")
            )

    run_activities = [
        (_run_stamp_as_utc(path), f"{CLAUDE_ACTIVITY_RUNS}/{path.name} (claude wake run)")
        for path in (root / CLAUDE_ACTIVITY_RUNS).glob("*.json")
    ]
    if run_activities:
        activities.append(max(run_activities, key=lambda item: item[0]))
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

    now_utc = now.astimezone(timezone.utc)
    parse_errors: list[dict] = []
    known_corrected: list[dict] = []
    corrections_path = root / "peer-chat.corrections.jsonl"
    corrections = _rows(corrections_path, parse_errors=parse_errors)
    try:
        anchor = _claude_activity_anchor(
            root,
            parse_errors,
            known_corrected,
            corrections,
            corrections_path,
            now_utc,
        )
        if anchor is None:
            return CheckResult(parse_errors=parse_errors, known_corrected=known_corrected)
        last_activity, source_ref = anchor
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        return CheckResult(
            parse_errors=parse_errors,
            known_corrected=known_corrected,
            skipped={"reason": f"{type(exc).__name__}: {exc}"},
        )

    activity_anchor = {"time_utc": last_activity.isoformat(), "source_ref": source_ref}
    if last_activity > now_utc:
        return CheckResult(
            parse_errors=parse_errors,
            known_corrected=known_corrected,
            activity_anchor=activity_anchor,
            clock_anomaly={
                "anchor_time_utc": last_activity.isoformat(),
                "now_utc": now_utc.isoformat(),
                "future_delta_hours": round((last_activity - now_utc).total_seconds() / 3600, 3),
                "source_ref": source_ref,
                "authority": "none",
            },
        )

    heartbeats = _codex_heartbeats_after(root, last_activity)
    silence_hours = (now_utc - last_activity).total_seconds() / 3600
    if silence_hours < threshold_hours or len(heartbeats) < min_heartbeats:
        return CheckResult(
            parse_errors=parse_errors, known_corrected=known_corrected, activity_anchor=activity_anchor
        )

    incident_suffix = hashlib.sha256(last_activity.isoformat().encode("utf-8")).hexdigest()[:12]
    incident_key = f"claude_silence:{incident_suffix}"
    alerts_path = root / "peer-health-alerts.jsonl"
    for _, row in _rows(alerts_path, parse_errors=parse_errors):
        if (
            row.get("direction") == "codex_to_claude"
            and row.get("incident_key") == incident_key
            and row.get("event") in {"raised", "reopened"}
        ):
            return CheckResult(
                parse_errors=parse_errors, known_corrected=known_corrected, activity_anchor=activity_anchor
            )

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
    return CheckResult(
        [event],
        parse_errors=parse_errors,
        known_corrected=known_corrected,
        activity_anchor=activity_anchor,
    )


def _orphan_frame_alert(*, root: Path, now: datetime) -> list[dict]:
    """Alert on terminal same-parent frame_open errors with semantic dual condition.

    Matches lines where: (a) stage is in the frame_open family (covers both old
    frame_open_stale_head and new frame_open), AND (b) line contains
    'causal parent must be terminal'. Also reports unrecognized terminal
    suffixes instead of silently returning empty.
    """
    log_path = root / "wake-cron.log"
    if not log_path.exists():
        return []

    streak: list[tuple[str, str]] = []
    parent: str | None = None
    unrecognized_count = 0
    unrecognized_first: str | None = None
    unrecognized_last: str | None = None

    for line in reversed(log_path.read_text(encoding="utf-8").splitlines()):
        match = _ATTEMPTED_PARENT.search(line)
        if match is None:
            break

        has_frame_open = _FRAME_OPEN_FAMILY.search(line) is not None
        has_causal = _CAUSAL_PARENT_TERMINAL.search(line) is not None

        if has_frame_open and has_causal:
            line_parent = match.group("parent")
            if parent is None:
                parent = line_parent
            elif line_parent != parent:
                break
            stamp = line.split(maxsplit=1)[0]
            streak.append((stamp, line_parent))
            unrecognized_count = 0
        else:
            if "ERROR" in line:
                unrecognized_count += 1
                stamp = line.split(maxsplit=1)[0]
                if unrecognized_last is None:
                    unrecognized_last = stamp
                unrecognized_first = stamp
            else:
                break

    alerts_path = root / "peer-health-alerts.jsonl"
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    appended: list[dict] = []
    now_str = now.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Report unrecognized terminal suffix (visible, not silent)
    if unrecognized_count >= ORPHAN_STREAK_MINIMUM and parent is None:
        event = {
            "id": uuid.uuid4().hex[:12],
            "time": now_str,
            "event": "raised",
            "kind": "unrecognized_terminal_suffix",
            "status": "suspected",
            "incident_key": "unrecognized_terminal_suffix",
            "consecutive_count": unrecognized_count,
            "first_error_time": unrecognized_first,
            "last_error_time": unrecognized_last,
            "source_ref": "wake-cron.log terminal suffix",
            "authority": "none",
            "note": "Sentinel scanned consecutive ERROR lines but could not match known frame_open + causal_parent pattern. Needs human review of wake-cron.log terminal suffix.",
        }
        with alerts_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        appended.append(event)

    if parent is not None and len(streak) >= ORPHAN_STREAK_MINIMUM:
        previous = None
        for _, row in _rows(alerts_path):
            if row.get("kind") == "orphan_frame" and row.get("parent_frame_id") == parent:
                previous = row
        if not (previous and previous.get("event") in {"raised", "reopened"}):
            chronological = list(reversed(streak))
            event = {
                "id": uuid.uuid4().hex[:12],
                "time": now_str,
                "event": "reopened" if previous and previous.get("event") == "resolved" else "raised",
                "kind": "orphan_frame",
                "status": "suspected",
                "incident_key": "orphan_frame:" + parent,
                "parent_frame_id": parent,
                "first_error_time": chronological[0][0],
                "last_error_time": chronological[-1][0],
                "consecutive_count": len(chronological),
                "source_ref": "wake-cron.log terminal suffix",
                "authority": "none",
            }
            with alerts_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            appended.append(event)

    return appended


def run_check(*, root: Path, now: datetime | None = None, threshold_hours: float = 6) -> CheckResult:
    """Run one check; malformed relevant activity makes the whole check fail safe."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    now_utc = now.astimezone(timezone.utc)
    orphan_alerts = _orphan_frame_alert(root=root, now=now)

    parse_errors: list[dict] = []
    known_corrected: list[dict] = []
    corrections_path = root / "peer-chat.corrections.jsonl"
    corrections = _rows(corrections_path, parse_errors=parse_errors)
    activities: list[tuple[datetime, str]] = []
    try:
        for name in ACTIVITY_FILES:
            path = root / name
            row_options = {}
            if name == "peer-chat.jsonl":
                row_options = {
                    "corrections": corrections,
                    "corrections_path": corrections_path,
                    "known_corrected": known_corrected,
                }
            source_head: tuple[int, dict] | None = None
            for line_number, row in _rows(path, parse_errors=parse_errors, **row_options):
                if row.get("from") == "codex":
                    source_head = (line_number, row)
            if source_head is not None:
                line_number, row = source_head
                stamp = _local_time_as_utc(row.get("time"))
                # An authored/unknown stamp claiming the future is a guess, not evidence:
                # drop the candidate so a tool-generated anchor can still measure silence.
                if _row_is_clocked(row) or stamp <= now_utc:
                    activities.append(
                        (stamp, f"{name}:{line_number}@{row['time']} (codex activity)")
                    )
        path = root / CODEX_HEARTBEAT_RUNS  # keeps a directory read failure honestly attributed
        run_activity = _newest_authentic_codex_run(root, parse_errors)
        if run_activity is not None:
            activities.append(run_activity)
    except (OSError, UnicodeError) as exc:
        return CheckResult(
            orphan_alerts,
            parse_errors=parse_errors,
            known_corrected=known_corrected,
            skipped={
                "reason": f"{type(exc).__name__}: {exc}",
                "source": path.name,
            },
        )
    except (ValueError, TypeError):
        return CheckResult(
            orphan_alerts, parse_errors=parse_errors, known_corrected=known_corrected
        )

    # With no trustworthy activity anchor, silence cannot be measured.
    if not activities:
        return CheckResult(
            orphan_alerts, parse_errors=parse_errors, known_corrected=known_corrected
        )
    last_activity, activity_source_ref = max(activities, key=lambda item: item[0])
    activity_anchor = {
        "time_utc": last_activity.isoformat(),
        "source_ref": activity_source_ref,
    }
    # Only a clock-authority or tool-generated anchor can still be in the future here;
    # that is a real host-clock anomaly and must stay visible rather than be swallowed.
    if last_activity > now_utc:
        return CheckResult(
            orphan_alerts,
            parse_errors=parse_errors,
            known_corrected=known_corrected,
            activity_anchor=activity_anchor,
            clock_anomaly={
                "anchor_time_utc": last_activity.isoformat(),
                "now_utc": now_utc.isoformat(),
                "future_delta_hours": round((last_activity - now_utc).total_seconds() / 3600, 3),
                "source_ref": activity_source_ref,
                "authority": "none",
            },
        )

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
            known_corrected=known_corrected,
            skipped={
                "reason": f"{type(exc).__name__}: {exc}",
                "source": "codex-inbox.jsonl/codex-inbox-replies.jsonl",
            },
            activity_anchor=activity_anchor,
        )
    except TypeError:
        return CheckResult(
            orphan_alerts,
            parse_errors=parse_errors,
            known_corrected=known_corrected,
            activity_anchor=activity_anchor,
        )

    pending = sorted(inbox_ids - replied_ids)
    return CheckResult(
        orphan_alerts + check_peer_liveness(
            alerts_path=root / "peer-health-alerts.jsonl",
            peer="codex",
            raised_by="claude",
            now=now_utc,
            last_activity_utc=last_activity,
            activity_source_ref=activity_source_ref,
            threshold_hours=threshold_hours,
            pending_item_ids=pending,
            backlog_source_ref="codex-inbox.jsonl ids minus codex-inbox-replies.jsonl reply_to ids",
        ),
        parse_errors=parse_errors,
        known_corrected=known_corrected,
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
    # §1.3: Export sentinel alerts to peer-chat + wake-deadlock-alert.md
    export_sentinel_alerts(
        appended_alerts=list(appended),
        alerts_path=args.root / "peer-health-alerts.jsonl",
        impl_dir=args.root,
        now=datetime.now(timezone.utc),
    )
    print(
        json.dumps(
            {
                "check": (
                    "skipped"
                    if appended.skipped
                    else "clock_anomaly"
                    if appended.clock_anomaly
                    else "completed"
                ),
                "appended": list(appended),
                "parse_errors": appended.parse_errors,
                "known_corrected": appended.known_corrected,
                "skipped": appended.skipped,
                "activity_anchor": appended.activity_anchor,
                "clock_anomaly": appended.clock_anomaly,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
