"""Claude wake producer for the zero-authority Codex liveness sidecar."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from peer_health import check_peer_liveness


LOCAL_TZ = timezone(timedelta(hours=9))
ACTIVITY_FILES = ("codex-inbox-replies.jsonl", "peer-chat.jsonl")


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
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise TypeError("JSONL row must be an object")
        except (json.JSONDecodeError, TypeError) as exc:
            if parse_errors is None:
                raise
            parse_errors.append(
                {
                    "source": f"{path.name}:{number}",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        result.append((number, row))
    return result


def _local_time_as_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("activity time is missing")
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return parsed.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def run_check(*, root: Path, now: datetime | None = None, threshold_hours: float = 6) -> CheckResult:
    """Run one check; malformed relevant activity makes the whole check fail safe."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

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
            parse_errors=parse_errors,
            skipped={
                "reason": f"{type(exc).__name__}: {exc}",
                "source": path.name,
            },
        )
    except (ValueError, TypeError):
        return CheckResult(parse_errors=parse_errors)

    # With no trustworthy activity anchor, silence cannot be measured.
    if not activities:
        return CheckResult(parse_errors=parse_errors)
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
            parse_errors=parse_errors,
            skipped={
                "reason": f"{type(exc).__name__}: {exc}",
                "source": "codex-inbox.jsonl/codex-inbox-replies.jsonl",
            },
            activity_anchor=activity_anchor,
        )
    except TypeError:
        return CheckResult(parse_errors=parse_errors, activity_anchor=activity_anchor)

    pending = sorted(inbox_ids - replied_ids)
    return CheckResult(
        check_peer_liveness(
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
    parser.add_argument("--threshold-hours", type=float, default=6)
    args = parser.parse_args(argv)
    try:
        appended = run_check(root=args.root, threshold_hours=args.threshold_hours)
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
