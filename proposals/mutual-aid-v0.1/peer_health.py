"""Zero-authority, append-only peer liveness sidecar.

This module does not change inboxes, activation, scheduling, or ownership.  A
caller checks one peer; only that caller may later resolve incidents it raised.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable


OPEN_EVENTS = {"raised", "reopened"}


def backlog_signature(item_ids: Iterable[str]) -> str:
    ids = sorted(set(item_ids))
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()[:12]


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _latest_by_key(rows: Iterable[dict], *, peer: str, raised_by: str) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        if row.get("peer") == peer and row.get("raised_by") == raised_by:
            latest[row["incident_key"]] = row
    return latest


def check_peer_liveness(
    *,
    alerts_path: Path,
    peer: str,
    raised_by: str,
    now: datetime,
    last_activity_utc: datetime,
    activity_source_ref: str,
    threshold_hours: float,
    pending_item_ids: Iterable[str],
    backlog_source_ref: str,
) -> list[dict]:
    """Append necessary lifecycle events and return only rows appended now."""
    if threshold_hours <= 0:
        raise ValueError("threshold_hours must be positive")
    pending = sorted(set(pending_item_ids))
    silence_hours = (now - last_activity_utc).total_seconds() / 3600
    if silence_hours < 0:
        future_skew_hours = -silence_hours
        if future_skew_hours > threshold_hours:
            return []
        silence_hours = 0.0

    rows = _read_jsonl(alerts_path)
    latest = _latest_by_key(rows, peer=peer, raised_by=raised_by)
    current_sig = backlog_signature(pending) if pending else None
    appended: list[dict] = []

    # Resolution is deliberately delayed until the original raiser checks the
    # peer again.  The recovering peer never resolves its own incident.
    for key, last in latest.items():
        if last.get("event") not in OPEN_EVENTS:
            continue
        incident_sig = key.split(":", 1)[1]
        if silence_hours <= threshold_hours or incident_sig != current_sig:
            event = _event_base(now, "resolved", raised_by, peer, key)
            event["reason"] = "peer_fresh" if silence_hours <= threshold_hours else "backlog_changed_or_cleared"
            _append_jsonl(alerts_path, event)
            appended.append(event)

    if not pending or silence_hours <= threshold_hours:
        return appended

    assert current_sig is not None
    key = f"{peer}:{current_sig}"
    previous = latest.get(key)
    if previous and previous.get("event") in OPEN_EVENTS:
        return appended

    event_name = "reopened" if previous and previous.get("event") == "resolved" else "raised"
    event = _event_base(now, event_name, raised_by, peer, key)
    event.update(
        {
            "silence": {
                "last_activity_utc": last_activity_utc.isoformat(),
                "source_ref": activity_source_ref,
                "silence_hours": round(silence_hours, 3),
                "threshold_hours": threshold_hours,
            },
            "backlog": {
                "count": len(pending),
                "items": pending,
                "signature": current_sig,
                "source_ref": backlog_source_ref,
            },
            "note": "Peer may be stuck; this is a heuristic suspicion requiring owner verification.",
        }
    )
    _append_jsonl(alerts_path, event)
    appended.append(event)
    return appended


def _event_base(now: datetime, event: str, raised_by: str, peer: str, incident_key: str) -> dict:
    return {
        "id": uuid.uuid4().hex[:12],
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "raised_by": raised_by,
        "peer": peer,
        "status": "suspected",
        "incident_key": incident_key,
    }


def append_hold(
    *, hold_path: Path, actor: str, peer: str, item_ref: str, now: datetime, event: str = "held"
) -> dict:
    """Append a visibility-only hold/release record; mutate no authority surface."""
    if event not in {"held", "released"}:
        raise ValueError("event must be held or released")
    row = {
        "id": uuid.uuid4().hex[:12],
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "actor": actor,
        "peer": peer,
        "item_ref": item_ref,
        "authority": "none",
    }
    _append_jsonl(hold_path, row)
    return row
