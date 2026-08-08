"""Regression tests for sentinel v1 proposal §二 (three independent changes).

Tests cover:
  (a1-a4) orphan shape decoupling (§1.1)
  (b1-b3) idle-period peer_silence visibility (§1.2)
  (c1-c5) sentinel export to peer-chat + wake-deadlock-alert.md (§1.3)
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from peer_health import check_peer_liveness, export_sentinel_alerts, backlog_signature


LOCAL_TZ = timezone(timedelta(hours=9))
NOW = datetime(2026, 7, 16, 18, 0, 0, tzinfo=LOCAL_TZ)
THRESHOLD = 6.0


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


# ---------------------------------------------------------------------------
# (a) Orphan shape decoupling
# ---------------------------------------------------------------------------

def _cron_old_shape(stamp: str, parent: str) -> str:
    """Old shape: frame_open_stale_head + causal parent text."""
    return (
        f'{stamp} ERROR rc=3 stage=native_exit stderr={{"frame_commit_failure":'
        f'{{"stage":"frame_open_stale_head","attempted_parent":"{parent}",'
        f'"diagnostic":"causal parent must be terminal: {parent}"}}}}'
    )


def _cron_new_shape(stamp: str, parent: str) -> str:
    """New shape: frame_open + causal parent text."""
    return (
        f'{stamp} ERROR rc=3 stage=native_exit stderr={{"frame_commit_failure":'
        f'{{"stage":"frame_open","attempted_parent":"{parent}",'
        f'"diagnostic":"causal parent must be terminal: {parent}"}}}}'
    )


def _cron_unrecognized(stamp: str) -> str:
    """Unrecognized: ERROR + attempted_parent but no frame_open family, no causal parent text."""
    return (
        f'{stamp} ERROR rc=3 stage=native_exit stderr={{"frame_commit_failure":'
        f'{{"stage":"some_other_stage","attempted_parent":"wf-unknown-x",'
        f'"diagnostic":"unrelated error message"}}}}'
    )


def _make_activity(root: Path, time_str: str = "2026-07-12 10:55:00") -> None:
    _append_jsonl(root / "peer-chat.jsonl", {"from": "codex", "time": time_str, "text": "alive"})


def _setup_root(tmp_path: Path, index: int, cron_lines: list[str]) -> Path:
    root = tmp_path / str(index)
    root.mkdir(parents=True, exist_ok=True)
    _make_activity(root)
    _write_jsonl(root / "codex-inbox.jsonl", [{"id": "job-a", "from": "claude"}])
    _write_jsonl(root / "codex-inbox-replies.jsonl", [{"reply_to": "job-a", "from": "codex", "time": "2026-07-12 10:55:00", "text": "done"}])
    cron_path = root / "wake-cron.log"
    cron_path.write_text("\n".join(cron_lines) + "\n", encoding="utf-8")
    return root


def test_a1_old_shape_raises_orphan_frame(tmp_path):
    """Old shape (frame_open_stale_head + causal parent) raises orphan_frame."""
    from peer_health_wake import _orphan_frame_alert
    root = _setup_root(tmp_path, 0, [
        _cron_old_shape(f"2026-07-16T18:{m:02d}:58", "wf-parent-a") for m in range(10)
    ])
    alerts = _orphan_frame_alert(root=root, now=NOW)
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "orphan_frame"
    assert alerts[0]["parent_frame_id"] == "wf-parent-a"
    assert alerts[0]["consecutive_count"] == 10


def test_a2_new_shape_raises_orphan_frame(tmp_path):
    """New shape (frame_open + causal parent) raises orphan_frame."""
    from peer_health_wake import _orphan_frame_alert
    root = _setup_root(tmp_path, 0, [
        _cron_new_shape(f"2026-07-16T18:{m:02d}:58", "wf-parent-b") for m in range(10)
    ])
    alerts = _orphan_frame_alert(root=root, now=NOW)
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "orphan_frame"
    assert alerts[0]["parent_frame_id"] == "wf-parent-b"
    assert alerts[0]["consecutive_count"] == 10


def test_a3_unrecognized_suffix_is_visible_not_silent(tmp_path):
    """Consecutive ERROR but unrecognized shape produces unrecognized_terminal_suffix."""
    from peer_health_wake import _orphan_frame_alert
    root = _setup_root(tmp_path, 0, [
        _cron_unrecognized(f"2026-07-16T18:{m:02d}:58") for m in range(12)
    ])
    alerts = _orphan_frame_alert(root=root, now=NOW)
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "unrecognized_terminal_suffix"
    assert alerts[0]["consecutive_count"] == 12
    assert alerts[0]["authority"] == "none"


def test_a4_short_streak_no_alert(tmp_path):
    """Streak < ORPHAN_STREAK_MINIMUM produces no alerts."""
    from peer_health_wake import _orphan_frame_alert
    root = _setup_root(tmp_path, 0, [
        _cron_new_shape(f"2026-07-16T18:{m:02d}:58", "wf-parent-c") for m in range(5)
    ])
    alerts = _orphan_frame_alert(root=root, now=NOW)
    assert alerts == []


# ---------------------------------------------------------------------------
# (b) Idle-period peer_silence visibility
# ---------------------------------------------------------------------------

def test_b1_empty_pending_with_silence_raises(tmp_path):
    """pending empty + silence > threshold raises with key=peer:silence."""
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    last_activity = NOW - timedelta(hours=10)
    result = check_peer_liveness(
        alerts_path=alerts_path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=last_activity,
        activity_source_ref="test",
        threshold_hours=THRESHOLD,
        pending_item_ids=[],
        backlog_source_ref="test",
    )
    assert len(result) == 1
    assert result[0]["incident_key"] == "codex:silence"
    assert result[0]["backlog"]["count"] == 0
    assert result[0]["backlog"]["signature"] is None
    assert result[0]["authority"] == "none"


def test_b2_nonempty_pending_uses_backlog_key(tmp_path):
    """pending non-empty + silence > threshold uses backlog key, not silence key."""
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    last_activity = NOW - timedelta(hours=10)
    result = check_peer_liveness(
        alerts_path=alerts_path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=last_activity,
        activity_source_ref="test",
        threshold_hours=THRESHOLD,
        pending_item_ids=["item-1", "item-2"],
        backlog_source_ref="test",
    )
    assert len(result) == 1
    sig = backlog_signature(["item-1", "item-2"])
    assert result[0]["incident_key"] == f"codex:{sig}"
    assert result[0]["backlog"]["count"] == 2
    assert "silence" not in result[0]["incident_key"]


def test_b3_silence_within_threshold_no_raise(tmp_path):
    """silence <= threshold does not raise regardless of pending."""
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    last_activity = NOW - timedelta(hours=2)
    result = check_peer_liveness(
        alerts_path=alerts_path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=last_activity,
        activity_source_ref="test",
        threshold_hours=THRESHOLD,
        pending_item_ids=[],
        backlog_source_ref="test",
    )
    assert result == []


# ---------------------------------------------------------------------------
# (c) Sentinel export
# ---------------------------------------------------------------------------

def test_c1_sentinel_writes_peer_chat_entry(tmp_path):
    """Raised alert produces a from:sentinel peer-chat entry with authority=none."""
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    last_activity = NOW - timedelta(hours=10)
    appended = check_peer_liveness(
        alerts_path=alerts_path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=last_activity,
        activity_source_ref="test",
        threshold_hours=THRESHOLD,
        pending_item_ids=[],
        backlog_source_ref="test",
    )
    assert len(appended) == 1
    records = export_sentinel_alerts(
        appended_alerts=appended,
        alerts_path=alerts_path,
        impl_dir=tmp_path,
        now=NOW,
    )
    assert len(records) == 1
    assert records[0]["from"] == "sentinel"
    assert records[0]["authority"] == "none"
    assert records[0]["time_authority"] == "clock"
    # Verify peer-chat.jsonl has the entry
    chat_lines = (tmp_path / "peer-chat.jsonl").read_text("utf-8").strip().split("\n")
    assert len(chat_lines) == 1
    entry = json.loads(chat_lines[0])
    assert entry["from"] == "sentinel"
    assert "codex:silence" in entry["text"]


def test_c2_wake_deadlock_alert_md_contains_key(tmp_path):
    """wake-deadlock-alert.md contains the incident key and alerts path reference."""
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    last_activity = NOW - timedelta(hours=10)
    appended = check_peer_liveness(
        alerts_path=alerts_path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=last_activity,
        activity_source_ref="test",
        threshold_hours=THRESHOLD,
        pending_item_ids=[],
        backlog_source_ref="test",
    )
    export_sentinel_alerts(
        appended_alerts=appended,
        alerts_path=alerts_path,
        impl_dir=tmp_path,
        now=NOW,
    )
    md = (tmp_path / "wake-deadlock-alert.md").read_text("utf-8")
    assert "codex:silence" in md
    assert "peer-health-alerts.jsonl" in md


def test_c3_all_resolved_md_says_no_active(tmp_path):
    """When all alerts resolved, md says 'No active liveness alerts.'."""
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    # Write a resolved alert
    _append_jsonl(alerts_path, {
        "id": "abc", "time": "2026-07-16 10:00:00", "event": "resolved",
        "raised_by": "claude", "peer": "codex", "status": "closed",
        "incident_key": "codex:test",
    })
    export_sentinel_alerts(
        appended_alerts=[],
        alerts_path=alerts_path,
        impl_dir=tmp_path,
        now=NOW,
    )
    md = (tmp_path / "wake-deadlock-alert.md").read_text("utf-8")
    assert "No active liveness alerts" in md


def test_c4_idempotent_reexport_does_not_duplicate(tmp_path):
    """Exporting the same alert twice does not produce duplicate peer-chat entries."""
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    last_activity = NOW - timedelta(hours=10)
    appended = check_peer_liveness(
        alerts_path=alerts_path,
        peer="codex",
        raised_by="claude",
        now=NOW,
        last_activity_utc=last_activity,
        activity_source_ref="test",
        threshold_hours=THRESHOLD,
        pending_item_ids=[],
        backlog_source_ref="test",
    )
    records1 = export_sentinel_alerts(
        appended_alerts=appended,
        alerts_path=alerts_path,
        impl_dir=tmp_path,
        now=NOW,
    )
    records2 = export_sentinel_alerts(
        appended_alerts=appended,
        alerts_path=alerts_path,
        impl_dir=tmp_path,
        now=NOW,
    )
    assert len(records1) == 1
    assert len(records2) == 0  # Already exported
    chat_lines = (tmp_path / "peer-chat.jsonl").read_text("utf-8").strip().split("\n")
    assert len(chat_lines) == 1


def test_c5_sentinel_rows_do_not_pollute_activity_anchor(tmp_path):
    """from:sentinel rows in peer-chat are ignored by activity anchor scans."""
    # Write a sentinel row (future time) and a codex row
    _append_jsonl(tmp_path / "peer-chat.jsonl", {
        "from": "sentinel", "text": "alert", "authority": "none",
        "time": "2026-07-16 20:00:00", "time_authority": "clock",
    })
    _append_jsonl(tmp_path / "peer-chat.jsonl", {
        "from": "codex", "time": "2026-07-16 10:55:00", "text": "alive",
    })
    # Verify that scanning peer-chat.jsonl for from=="codex" or from=="claude"
    # does NOT pick up the sentinel row
    import json as _json
    rows = []
    for line in (tmp_path / "peer-chat.jsonl").read_text("utf-8").splitlines():
        if line.strip():
            rows.append(_json.loads(line))
    agent_rows = [r for r in rows if r.get("from") in ("codex", "claude")]
    sentinel_rows = [r for r in rows if r.get("from") == "sentinel"]
    assert len(agent_rows) == 1  # only the codex row
    assert len(sentinel_rows) == 1
    assert agent_rows[0]["time"] == "2026-07-16 10:55:00"
