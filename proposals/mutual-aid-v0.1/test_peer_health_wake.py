import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from peer_health_wake import main, run_check, run_reverse_check


NOW = datetime(2026, 7, 12, 2, tzinfo=timezone.utc)  # 11:00 UTC+9


def append(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def fixture(root: Path, activity_time="2026-07-12 10:55:00", replied=False):
    append(root / "peer-chat.jsonl", {"from": "codex", "time": activity_time, "text": "alive"})
    append(root / "codex-inbox.jsonl", {"id": "job-a", "from": "claude"})
    if replied:
        append(
            root / "codex-inbox-replies.jsonl",
            {"reply_to": "job-a", "from": "codex", "time": activity_time, "text": "done"},
        )


def alerts(root):
    path = root / "peer-health-alerts.jsonl"
    return [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def cron_line(stamp: str, parent: str) -> str:
    return (
        f'{stamp} ERROR rc=3 stage=native_exit stderr={{"frame_commit_failure":'
        f'{{"stage":"frame_open_stale_head","attempted_parent":"{parent}"}}}}'
    )


def write_cron(root: Path, lines: list[str]) -> None:
    (root / "wake-cron.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reverse_fixture(root: Path, *, claude_time="2026-07-16 16:00:00", heartbeat_count=3):
    append(root / "peer-chat.jsonl", {"from": "claude", "time": "2026-07-16 15:00:00", "text": "here"})
    append(
        root / "concurrent-receipts.jsonl",
        {"wake_id": "claude-wake-test", "time": "2026-07-16 15:30:00", "work_performed": False},
    )
    runs = root / "wake-agent-runs"
    runs.mkdir(parents=True)
    run_name = claude_time.replace(" ", "T").replace(":", "-")
    (runs / f"{run_name}.json").write_text("{}", encoding="utf-8")
    codex_runs = root / "wake-codex-runs"
    codex_runs.mkdir(parents=True)
    for hour in range(17, 17 + heartbeat_count):
        (codex_runs / f"2026-07-16T{hour:02d}-00-00.jsonl").write_text("", encoding="utf-8")


def test_terminal_same_parent_streak_raises_orphan_alert_with_evidence(tmp_path):
    fixture(tmp_path)
    write_cron(tmp_path, [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)])

    result = run_check(root=tmp_path, now=NOW)

    assert len(result) == 1
    alert = result[0]
    assert alert["kind"] == "orphan_frame"
    assert alert["parent_frame_id"] == "wf-parent-a"
    assert alert["first_error_time"] == "2026-07-16T18:00:58"
    assert alert["last_error_time"] == "2026-07-16T18:09:58"
    assert alert["consecutive_count"] == 10
    assert alert["authority"] == "none"


def test_real_current_log_tail_does_not_raise_orphan_alert(tmp_path):
    fixture(tmp_path)
    real_log = Path(__file__).resolve().parents[1] / "bounded-scheduler-v0.1" / "impl" / "wake-cron.log"
    (tmp_path / "wake-cron.log").write_bytes(real_log.read_bytes())

    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_success_line_truncates_old_orphan_streak(tmp_path):
    fixture(tmp_path)
    lines = [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)]
    lines.append("2026-07-16T18:10:58 wake ok stop=quiescent frame=wf-success")
    write_cron(tmp_path, lines)

    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_unresolved_same_parent_orphan_alert_is_deduplicated(tmp_path):
    fixture(tmp_path)
    write_cron(tmp_path, [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)])

    assert len(run_check(root=tmp_path, now=NOW)) == 1
    assert run_check(root=tmp_path, now=NOW) == []
    assert len(alerts(tmp_path)) == 1


def test_real_shape_fresh_activity_does_not_raise(tmp_path):
    fixture(tmp_path)
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_small_future_activity_is_fresh_end_to_end(tmp_path):
    future_local = (NOW + timedelta(minutes=5)).astimezone(
        timezone(timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M:%S")
    fixture(tmp_path, activity_time=future_local)
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_silent_pending_raises_once_and_is_idempotent(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    first = run_check(root=tmp_path, now=NOW)
    assert len(first) == 1 and first[0]["event"] == "raised"
    assert first[0]["raised_by"] == "claude" and first[0]["peer"] == "codex"
    assert first[0]["status"] == "suspected"
    assert first[0]["silence"]["source_ref"] and first[0]["backlog"]["source_ref"]
    assert run_check(root=tmp_path, now=NOW) == []
    assert len(alerts(tmp_path)) == 1


def test_reply_clears_backlog_and_resolves_once(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    run_check(root=tmp_path, now=NOW)
    append(
        tmp_path / "codex-inbox-replies.jsonl",
        {"reply_to": "job-a", "from": "codex", "time": "2026-07-12 10:58:00", "text": "done"},
    )
    resolved = run_check(root=tmp_path, now=NOW)
    assert len(resolved) == 1 and resolved[0]["event"] == "resolved"
    assert run_check(root=tmp_path, now=NOW) == []


def test_malformed_or_missing_relevant_time_fails_safe_whole_round(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    append(tmp_path / "peer-chat.jsonl", {"from": "codex", "time": "not-a-time", "text": "newer bad"})
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []

    tmp_path.joinpath("peer-chat.jsonl").write_text(
        json.dumps({"from": "codex", "text": "missing time"}) + "\n", encoding="utf-8"
    )
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_malformed_json_row_is_visible_without_discarding_good_anchor(tmp_path):
    fixture(tmp_path)
    with (tmp_path / "peer-chat.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(r'{"from":"claude","text":"D:\bad\escape"}' + "\n")

    result = run_check(root=tmp_path, now=NOW)

    assert result == []
    assert result.activity_anchor == {
        "time_utc": "2026-07-12T01:55:00+00:00",
        "source_ref": "peer-chat.jsonl:1@2026-07-12 10:55:00 (codex activity)",
    }
    assert len(result.parse_errors) == 1
    assert result.parse_errors[0]["source"] == (tmp_path / "peer-chat.jsonl").as_posix()
    assert result.parse_errors[0]["line"] == 2
    assert result.parse_errors[0]["reason_code"] == "invalid_json"


def test_whole_file_read_failure_is_visible_in_cli(tmp_path, monkeypatch, capsys):
    fixture(tmp_path)
    original = Path.read_bytes

    def unreadable(path, *args, **kwargs):
        if path.name == "peer-chat.jsonl":
            raise PermissionError("test unreadable file")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    assert main(["--root", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["check"] == "skipped"
    assert report["appended"] == []
    assert report["skipped"]["source"] == "peer-chat.jsonl"
    assert "PermissionError" in report["skipped"]["reason"]


def test_authority_surfaces_are_byte_identical(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    protected = [tmp_path / "owner-inbox.jsonl", tmp_path / "activation.state", tmp_path / "codex-inbox.jsonl"]
    for path in protected[:2]:
        path.write_bytes((path.name + "\n").encode())
    before = {path: path.read_bytes() for path in protected}
    run_check(root=tmp_path, now=NOW)
    assert {path: path.read_bytes() for path in protected} == before


def test_reverse_silence_with_three_codex_heartbeats_raises_complete_alert(tmp_path):
    reverse_fixture(tmp_path)
    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))
    assert len(result) == 1
    alert = result[0]
    assert alert["direction"] == "codex_to_claude"
    assert alert["peer"] == "claude" and alert["raised_by"] == "codex"
    assert alert["silence"]["threshold_hours"] == 4
    assert alert["silence"]["source_ref"].startswith("wake-agent-runs/")
    assert alert["observer_heartbeats"]["count"] == 3
    assert alert["authority"] == "none"


def test_reverse_fresh_claude_does_not_alert(tmp_path):
    reverse_fixture(tmp_path, claude_time="2026-07-16 20:00:00")
    assert run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc)) == []
    assert not (tmp_path / "peer-health-alerts.jsonl").exists()


def test_reverse_unresolved_same_anchor_is_reported_once(tmp_path):
    reverse_fixture(tmp_path)
    now = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    assert len(run_reverse_check(root=tmp_path, now=now)) == 1
    assert run_reverse_check(root=tmp_path, now=now) == []
    assert len(alerts(tmp_path)) == 1
