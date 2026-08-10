"""Regression tests for sentinel-view-incident-collapse-v0.1 (dual-signed 2026-08-10).

Covers PROPOSAL.md 1.1 (incident_key fold to last physical event before the
OPEN_EVENTS filter) and 1.2 (orphan_frame rows render consecutive_count /
last_error_time instead of a silent "silence=?h"), plus the cosigned
acceptance item: the fold key is (incident_key, raised_by, peer), so one
raiser's resolved row must not suppress another raiser's raised row.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from peer_health import export_sentinel_alerts


NOW = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)


def _row(rid, event, incident_key, *, raised_by="claude", peer="codex", **extra):
    row = {
        "id": rid,
        "time": "2026-08-10 10:00:00",
        "event": event,
        "raised_by": raised_by,
        "peer": peer,
        "status": "suspected" if event in {"raised", "reopened"} else "closed",
        "incident_key": incident_key,
    }
    row.update(extra)
    return row


def _export(rows, tmp_path):
    alerts_path = tmp_path / "peer-health-alerts.jsonl"
    alerts_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    export_sentinel_alerts(
        appended_alerts=[],
        alerts_path=alerts_path,
        impl_dir=tmp_path,
        now=NOW,
    )
    return (tmp_path / "wake-deadlock-alert.md").read_text(encoding="utf-8")


def test_raised_then_resolved_is_not_active(tmp_path):
    md = _export(
        [
            _row("a1", "raised", "codex:dc28eaeb4843"),
            _row("a2", "resolved", "codex:dc28eaeb4843"),
        ],
        tmp_path,
    )
    assert "No active liveness alerts" in md
    assert "dc28eaeb4843" not in md


def test_raised_resolved_reopened_is_active(tmp_path):
    md = _export(
        [
            _row("a1", "raised", "codex:test"),
            _row("a2", "resolved", "codex:test"),
            _row("a3", "reopened", "codex:test"),
        ],
        tmp_path,
    )
    assert "**codex:test** (reopened)" in md


def test_orphan_frame_renders_count_and_last_error(tmp_path):
    md = _export(
        [
            _row(
                "orphan-1",
                "raised",
                "orphan_frame:wf-test",
                raised_by=None,
                peer=None,
                kind="orphan_frame",
                first_error_time="2026-07-22T11:31:58",
                last_error_time="2026-07-22T12:02:58",
                consecutive_count=15,
                source_ref="wake-cron.log terminal suffix",
                authority="none",
            )
        ],
        tmp_path,
    )
    assert "orphan_frame:wf-test" in md
    assert "count=15, last_error=2026-07-22T12:02:58" in md
    assert "silence=?h" not in md


def test_silence_row_still_renders_silence_hours(tmp_path):
    md = _export([_row("a1", "raised", "codex:test", silence={"silence_hours": 7.9})], tmp_path)
    assert "silence=7.9h" in md


def test_fold_key_includes_raised_by_peer_so_resolved_does_not_suppress_other_raiser(tmp_path):
    md = _export(
        [
            _row("a1", "raised", "shared:key", raised_by="claude", peer="codex"),
            _row("a2", "resolved", "shared:key", raised_by="claude", peer="codex"),
            _row("a3", "raised", "shared:key", raised_by="owner", peer="codex"),
        ],
        tmp_path,
    )
    assert md.count("**shared:key**") == 1
    assert "**shared:key** (raised)" in md


def test_real_ledger_shape_active_is_only_orphan_frames(tmp_path):
    """Mirror of the live peer-health-alerts.jsonl: one resolved pair plus
    four orphan_frame rows -> exactly the four orphan_frame rows are active."""
    rows = [
        _row(
            "orphan-1", "raised", "orphan_frame:wf-20260722-021701-645652",
            raised_by=None, peer=None, kind="orphan_frame",
            last_error_time="2026-07-22T12:02:58", consecutive_count=15,
        ),
        _row(
            "orphan-2", "raised", "orphan_frame:wf-20260722-162354-4d82de",
            raised_by=None, peer=None, kind="orphan_frame",
            last_error_time="2026-07-23T08:04:58", consecutive_count=182,
        ),
        _row(
            "a3", "raised", "codex:dc28eaeb4843", raised_by="claude", peer="codex",
            silence={"silence_hours": 7.911},
        ),
        _row("a4", "resolved", "codex:dc28eaeb4843", raised_by="claude", peer="codex"),
        _row(
            "orphan-3", "raised", "orphan_frame:wf-20260730-102159-d54176",
            raised_by=None, peer=None, kind="orphan_frame",
            last_error_time="2026-07-30T21:18:58", consecutive_count=37,
        ),
        _row(
            "orphan-4", "raised", "orphan_frame:wf-20260730-153428-dff33a",
            raised_by=None, peer=None, kind="orphan_frame",
            last_error_time="2026-07-31T08:02:58", consecutive_count=203,
        ),
    ]
    md = _export(rows, tmp_path)
    assert md.count("- **") == 4
    assert "dc28eaeb4843" not in md
    for key in (
        "wf-20260722-021701-645652",
        "wf-20260722-162354-4d82de",
        "wf-20260730-102159-d54176",
        "wf-20260730-153428-dff33a",
    ):
        assert key in md
