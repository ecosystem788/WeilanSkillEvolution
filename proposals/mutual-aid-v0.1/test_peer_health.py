import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from peer_health import append_hold, backlog_signature, check_peer_liveness


NOW = datetime(2026, 7, 12, 9, tzinfo=timezone.utc)


def check(path: Path, *, old_hours=7, pending=("job-b", "job-a")):
    return check_peer_liveness(
        alerts_path=path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=NOW - timedelta(hours=old_hours),
        activity_source_ref="peer-chat.jsonl@codex-last-line",
        threshold_hours=6,
        pending_item_ids=pending,
        backlog_source_ref="codex-inbox.jsonl - codex-inbox-replies.jsonl",
    )


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_first_alert_has_stable_identity_and_evidence(tmp_path):
    path = tmp_path / "peer-health-alerts.jsonl"
    appended = check(path)
    assert len(appended) == 1
    event = appended[0]
    assert event["event"] == "raised" and event["status"] == "suspected"
    assert event["incident_key"] == f"codex:{backlog_signature(['job-a', 'job-b'])}"
    assert event["silence"]["threshold_hours"] == 6
    assert event["silence"]["source_ref"] and event["backlog"]["source_ref"]


def test_unchanged_backlog_does_not_repeat_across_longer_silence(tmp_path):
    path = tmp_path / "peer-health-alerts.jsonl"
    check(path, old_hours=7)
    before = path.read_bytes()
    check(path, old_hours=25)
    assert path.read_bytes() == before


def test_original_raiser_resolves_then_reopens_same_signature(tmp_path):
    path = tmp_path / "peer-health-alerts.jsonl"
    check(path)
    assert [e["event"] for e in check(path, old_hours=1, pending=())] == ["resolved"]
    assert [e["event"] for e in check(path)] == ["reopened"]
    assert [e["event"] for e in rows(path)] == ["raised", "resolved", "reopened"]


def test_fresh_peer_or_empty_backlog_does_not_raise(tmp_path):
    fresh = tmp_path / "fresh.jsonl"
    empty = tmp_path / "empty.jsonl"
    assert check(fresh, old_hours=1) == [] and not fresh.exists()
    assert check(empty, pending=()) == [] and not empty.exists()


def test_small_future_skew_is_fresh_and_resolves_open_incident(tmp_path):
    path = tmp_path / "peer-health-alerts.jsonl"
    check(path)
    appended = check_peer_liveness(
        alerts_path=path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=NOW + timedelta(minutes=5),
        activity_source_ref="peer-chat.jsonl@future-by-5m",
        threshold_hours=6,
        pending_item_ids=("job-a", "job-b"),
        backlog_source_ref="codex-inbox.jsonl - codex-inbox-replies.jsonl",
    )
    assert [event["event"] for event in appended] == ["resolved"]
    assert appended[0]["reason"] == "peer_fresh"


def test_large_future_skew_returns_without_touching_alert_lifecycle(tmp_path):
    path = tmp_path / "peer-health-alerts.jsonl"
    check(path)
    before = path.read_bytes()
    appended = check_peer_liveness(
        alerts_path=path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=NOW + timedelta(hours=100),
        activity_source_ref="peer-chat.jsonl@future-by-100h",
        threshold_hours=6,
        pending_item_ids=("job-a", "job-b"),
        backlog_source_ref="codex-inbox.jsonl - codex-inbox-replies.jsonl",
    )
    assert appended == []
    assert path.read_bytes() == before


def test_hold_changes_only_hold_sidecar(tmp_path):
    protected = [tmp_path / name for name in ("owner-inbox.jsonl", "activation.state", "codex-inbox.jsonl")]
    for path in protected:
        path.write_bytes((path.name + "\n").encode())
    before = {path: path.read_bytes() for path in protected}
    hold = tmp_path / "peer-hold.jsonl"
    row = append_hold(hold_path=hold, actor="claude", peer="codex", item_ref="job-a", now=NOW)
    assert row["authority"] == "none" and hold.exists()
    assert {path: path.read_bytes() for path in protected} == before
